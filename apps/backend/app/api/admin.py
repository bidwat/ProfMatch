import subprocess
from typing import Any
import asyncio
import json
import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from apps.backend.app.api.auth import get_current_user
from apps.backend.app.db import get_session
from apps.backend.app.models.auth import User
from apps.backend.app.services.admin_scan_service import AdminScanService
from apps.backend.app.services.import_service import ImportService
from apps.backend.app.services.professor_service import ProfessorService
from apps.backend.app.services.recommendation_service import RecommendationService
from apps.backend.app.services.openalex_publication_service import OpenAlexPublicationRevisionService
from apps.backend.app.services.scan_job_service import ScanJobService


class ScanPaths(BaseModel):
    validation: str | None = None
    scan_manifest: str | None = None
    openrouter_audit: str | None = None
    raw: str | None = None
    raw_manifest: str | None = None
    processed_professors: str | None = None
    processed_publications: str | None = None


class ScanSummary(BaseModel):
    id: str
    date: str | None = None
    school_slug: str
    university: str
    department: str | None = None
    adapter_name: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    run_status: str | None = None
    qa_status: str | None = None
    db_import_allowed: bool
    professors: int
    publications: int
    duplicates: int
    errors: int
    warnings: int
    total_issues: int
    openrouter_status: str | None = None
    openrouter_model: str | None = None
    issue_breakdown: dict[str, Any] = Field(default_factory=dict)
    issues_preview: list[dict[str, Any]] = Field(default_factory=list)
    duplicate_candidates: list[dict[str, Any]] = Field(default_factory=list)
    validation_filename: str
    manifest_filename: str
    openrouter_audit_filename: str
    paths: ScanPaths


class ListScansResponse(BaseModel):
    scans: list[ScanSummary] = Field(default_factory=list)


class ScanDetailResponse(ScanSummary):
    validation: dict[str, Any] | None = None
    scan_manifest: dict[str, Any] | None = None
    openrouter_audit: dict[str, Any] | None = None
    professors_preview: list[dict[str, Any]] = Field(default_factory=list)
    publications_preview: list[dict[str, Any]] = Field(default_factory=list)


class RunScanRequest(BaseModel):
    adapter: str
    enrich_profiles: bool = True
    enrich_publications: bool = False


def validate_public_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid http or https URL")
    hostname = parsed.hostname or ""
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or hostname.endswith(".local"):
        raise ValueError("Faculty page URL must be publicly reachable")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("Faculty page URL must be publicly reachable")
    except ValueError as exc:
        if "publicly reachable" in str(exc):
            raise
    return url


class AgenticOnboardRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)
    university: str = "Unknown University"
    department: str = "Computer Science"
    automatic: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_public_url(value)


class IndexedDepartment(BaseModel):
    university: str
    department: str
    professor_count: int
    publication_count: int


class IndexedDepartmentsResponse(BaseModel):
    groups: list[IndexedDepartment] = Field(default_factory=list)


class RefreshIndexedDepartmentRequest(BaseModel):
    university: str
    department: str
    faculty_page_url: str = Field(..., min_length=8, max_length=2000)
    automatic: bool = False

    @field_validator("faculty_page_url")
    @classmethod
    def validate_faculty_page_url(cls, value: str) -> str:
        return validate_public_url(value)


class DeleteIndexedDepartmentRequest(BaseModel):
    university: str
    department: str
    confirm: bool = False


class ScanJobItemRequest(BaseModel):
    university: str = Field(..., min_length=1, max_length=300)
    department: str = Field(default="Computer Science", min_length=1, max_length=300)
    faculty_url: str = Field(..., min_length=8, max_length=2000)

    @field_validator("faculty_url")
    @classmethod
    def validate_faculty_url(cls, value: str) -> str:
        return validate_public_url(value)


class CreateScanJobRequest(BaseModel):
    items: list[ScanJobItemRequest] = Field(..., min_length=1, max_length=20)
    settings: dict[str, Any] = Field(default_factory=dict)


class RevisePublicationsRequest(BaseModel):
    max_publications: int = Field(default=10, ge=1, le=25)
    use_llm_verification: bool = False


class RefreshIndexedPublicationsRequest(BaseModel):
    university: str
    department: str
    max_publications: int = Field(default=10, ge=1, le=25)
    max_professors: int = Field(default=250, ge=1, le=500)
    regenerate_summaries: bool = False


class EnrichIndexedProfilesRequest(BaseModel):
    university: str
    department: str
    max_professors: int = Field(default=250, ge=1, le=500)


router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user


@router.post("/scan-jobs")
def create_scan_job(req: CreateScanJobRequest, current_user: User = Depends(require_admin), session: Session = Depends(get_session)):
    service = ScanJobService(session)
    job = service.create_scan_job(
        items=[item.model_dump() for item in req.items],
        settings=req.settings,
        created_by_user_id=current_user.id,
    )
    return {"job_id": job.id, "status": job.status, "total_tasks": job.total_tasks, "job": job}


@router.get("/scan-jobs")
def list_scan_jobs(status: str | None = None, limit: int = 50, offset: int = 0, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"jobs": ScanJobService(session).list_scan_jobs(status=status, limit=limit, offset=offset)}


@router.get("/scan-jobs/{job_id}")
def get_scan_job(job_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    service = ScanJobService(session)
    job = service.get_scan_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {"job": job}


@router.post("/scan-jobs/{job_id}/cancel")
def cancel_scan_job(job_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    job = ScanJobService(session).cancel_scan_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {"job": job}


@router.get("/scan-jobs/{job_id}/tasks")
def list_scan_job_tasks(job_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"tasks": ScanJobService(session).list_scan_tasks(job_id)}


@router.get("/scan-jobs/{job_id}/results")
def list_scan_job_results(job_id: int, status: str | None = None, limit: int = 200, offset: int = 0, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"results": ScanJobService(session).list_scan_results(job_id, status=status, limit=limit, offset=offset)}


@router.get("/scan-jobs/{job_id}/logs")
def list_scan_job_logs(job_id: int, level: str | None = None, limit: int = 200, offset: int = 0, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"logs": ScanJobService(session).list_scan_logs(job_id, level=level, limit=limit, offset=offset)}


@router.post("/scan-results/{result_id}/approve")
def approve_scan_result(result_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    result = ScanJobService(session).approve_scan_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return {"result": result}


@router.post("/scan-results/{result_id}/reject")
def reject_scan_result(result_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    result = ScanJobService(session).reject_scan_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return {"result": result}


@router.post("/scan-results/{result_id}/import")
def import_scan_result(result_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    result = ScanJobService(session).import_scan_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return {"result": result}


@router.post("/scan-jobs/{job_id}/fetch-publications")
def fetch_scan_job_publications(job_id: int, req: RevisePublicationsRequest, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    job = ScanJobService(session).get_scan_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    summary = OpenAlexPublicationRevisionService(session).fetch_job_publications(
        job_id,
        max_publications=req.max_publications,
        use_llm_verification=req.use_llm_verification,
    )
    return {"summary": summary}


@router.post("/scan-jobs/{job_id}/revise-publications")
def revise_scan_job_publications(job_id: int, req: RevisePublicationsRequest, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    return fetch_scan_job_publications(job_id, req, _, session)


@router.post("/scan-jobs/{job_id}/import-approved")
def import_approved_scan_results(job_id: int, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    service = ScanJobService(session)
    imported = []
    for result in service.list_scan_results(job_id, status="approved", limit=1000):
        imported_result = service.import_scan_result(result.id)
        if imported_result:
            imported.append(imported_result)
    return {"imported_count": len(imported), "results": imported}


@router.get("/adapters")
def list_adapters(_: User = Depends(require_admin)):
    from scripts.project.run_university_scan import ADAPTERS
    return {"adapters": list(ADAPTERS.keys())}


def set_job_status(status: str, message: str):
    from apps.backend.app.db import PROJECT_ROOT
    import json
    status_file = PROJECT_ROOT / "data" / "qa" / "job_status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps({"status": status, "message": message}))


def execute_scan_task(adapter: str, enrich_profiles: bool, enrich_publications: bool):
    import sys
    from apps.backend.app.db import PROJECT_ROOT
    script = PROJECT_ROOT / "scripts" / "project" / "run_university_scan.py"
    
    set_job_status("running", f"Running scan for adapter '{adapter}'...")
    
    cmd = [
        sys.executable, str(script),
        "--adapter", adapter,
        "--output-root", str(PROJECT_ROOT)
    ]
    if enrich_profiles:
        cmd.append("--enrich-profiles")
    else:
        cmd.append("--no-enrich-profiles")
        
    if enrich_publications:
        cmd.append("--enrich-publications")
    else:
        cmd.append("--no-enrich-publications")
        
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True)
    if result.returncode == 0:
        set_job_status("idle", "No active jobs")
    else:
        import logging
        logger = logging.getLogger("profmatch.agentic")
        logger.error(f"Test scan failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        set_job_status("error", f"Test scan failed: {result.stderr.splitlines()[-1] if result.stderr.splitlines() else 'Unknown error'}")


def execute_agentic_onboarding(url: str):
    from apps.backend.app.services.agentic_scraper_service import AgenticScraperService
    service = AgenticScraperService()
    try:
        set_job_status("running", f"Agent analyzing {url}...")
        result = service.generate_adapter(url)
        if result["status"] == "success":
            set_job_status("running", f"Successfully generated {result['adapter']} adapter. Running test scan...")
            execute_scan_task(
                adapter=result["adapter"],
                enrich_profiles=False,
                enrich_publications=False
            )
        else:
            set_job_status("error", f"Agentic onboarding rejected: {result.get('message')}")
    except Exception as e:
        import logging
        logging.getLogger("profmatch.agentic").error(f"Agentic onboarding failed: {e}", exc_info=True)
        set_job_status("error", f"Agentic onboarding failed: {e}")


@router.post("/agentic/onboard")
def onboard_university(req: AgenticOnboardRequest, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    job_id = service.create_job(req.url, req.university, req.department)
    
    async def run_bg():
        if req.automatic:
            await service.run_automatic_pipeline(job_id)
        else:
            await service.run_extract_roster(job_id)
        
    import asyncio
    background_tasks.add_task(lambda: asyncio.run(run_bg()))
    return {"status": "started", "job_id": job_id, "message": "Agentic extraction started in the background."}

def _summarize_agentic_jobs() -> list[dict[str, Any]]:
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    jobs = service.list_jobs()
    for j in jobs:
        if "professors" in j:
            j["professor_count"] = len(j["professors"])
            del j["professors"]
    return jobs


def _job_group(job: dict[str, Any]) -> str:
    status = str(job.get("status") or "").lower()
    step = str(job.get("step") or "").lower()
    if status in {"running", "pending"}:
        return "ongoing"
    if status == "completed" and step not in {"publish", "auto_done"}:
        return "ready_to_publish"
    if status == "completed":
        return "completed"
    if status == "error":
        return "completed"
    return "ongoing"


@router.get("/agentic/jobs")
def list_agentic_jobs(_: User = Depends(require_admin)):
    return {"jobs": _summarize_agentic_jobs()}


@router.get("/agentic/jobs/grouped")
def list_agentic_jobs_grouped(_: User = Depends(require_admin)):
    grouped = {"ongoing": [], "ready_to_publish": [], "completed": []}
    for job in _summarize_agentic_jobs():
        grouped[_job_group(job)].append(job)
    return grouped

@router.get("/agentic/job/{job_id}/events")
async def stream_agentic_job(job_id: str, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService

    async def events():
        service = AgenticOnboardingService()
        while True:
            job = service.get_job(job_id)
            if not job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                break
            yield f"data: {json.dumps(job)}\n\n"
            if str(job.get("status") or "").lower() not in {"running", "pending"}:
                break
            await asyncio.sleep(5)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/agentic/job/{job_id}")
def get_agentic_job(job_id: str, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/agentic/job/{job_id}/stop")
def stop_agentic_job(job_id: str, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    if not service.stop_job(job_id):
        raise HTTPException(status_code=400, detail="Could not stop job. It may not be running.")
    return {"status": "stopped", "message": "Job stopped successfully."}

@router.delete("/agentic/job/{job_id}")
def delete_agentic_job(job_id: str, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    if not service.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"status": "deleted"}

@router.post("/agentic/job/{job_id}/enrich-homepage")
def agentic_enrich_homepage(job_id: str, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    
    async def run_bg():
        await service.run_enrich_homepages(job_id)
        
    import asyncio
    background_tasks.add_task(lambda: asyncio.run(run_bg()))
    return {"status": "started", "message": "Enriching homepages in background..."}

@router.post("/agentic/job/{job_id}/fetch-publications")
def agentic_fetch_publications(job_id: str, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    background_tasks.add_task(service.run_fetch_publications, job_id=job_id)
    return {"status": "started", "message": "Fetching publications in background..."}

@router.post("/agentic/job/{job_id}/generate-summary")
def agentic_generate_summary(job_id: str, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    background_tasks.add_task(service.run_generate_summary, job_id=job_id)
    return {"status": "started", "message": "Generating AI summaries in background..."}

@router.post("/agentic/job/{job_id}/publish")
def agentic_publish(job_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), _: User = Depends(require_admin)):
    from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService
    service = AgenticOnboardingService()
    
    # We must run it synchronously or pass a fresh session if it was truly background, 
    # but for this MVP let's just execute it inline to avoid session thread issues or we can create a fresh session inside the service.
    # We will pass a function that creates its own session to the background task.
    def bg_publish():
        from apps.backend.app.db import engine
        from sqlmodel import Session as SMSession
        with SMSession(engine) as s:
            service.run_publish(job_id, s)
            
    background_tasks.add_task(bg_publish)
    return {"status": "started", "message": "Publishing to SQLite in background..."}


@router.get("/indexed-departments", response_model=IndexedDepartmentsResponse)
def list_indexed_departments(_: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"groups": ProfessorService(session).list_indexed_groups()}


@router.get("/recommendations")
def list_recommendations(_: User = Depends(require_admin)):
    return {"requests": RecommendationService().list()}


@router.post("/indexed-departments/refresh")
def refresh_indexed_department(req: RefreshIndexedDepartmentRequest, current_user: User = Depends(require_admin), session: Session = Depends(get_session)):
    job = ScanJobService(session).create_scan_job(
        items=[{"university": req.university, "department": req.department, "faculty_url": req.faculty_page_url}],
        settings={"fetch_publications": True, "openalex_publications": True, "max_publications": 10, "regenerate_summaries": True},
        created_by_user_id=current_user.id,
        job_type="refresh_existing_department",
    )
    return {"status": "started", "job_id": str(job.id), "message": "Durable OpenAlex-backed refresh queued. Existing indexed data is unchanged until candidates are approved/imported."}


def _run_indexed_publication_refresh(req: RefreshIndexedPublicationsRequest) -> None:
    from apps.backend.app.db import engine
    with Session(engine) as session:
        OpenAlexPublicationRevisionService(session).refresh_indexed_department_publications(
            university=req.university,
            department=req.department,
            max_publications=req.max_publications,
            max_professors=req.max_professors,
            regenerate_summaries=False,
        )


def _run_indexed_profile_enrichment(req: EnrichIndexedProfilesRequest) -> None:
    from apps.backend.app.db import engine
    with Session(engine) as session:
        OpenAlexPublicationRevisionService(session).enrich_indexed_department_profiles(
            university=req.university,
            department=req.department,
            max_professors=req.max_professors,
        )


@router.post("/indexed-departments/fetch-publications")
def refresh_indexed_department_publications(req: RefreshIndexedPublicationsRequest, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    background_tasks.add_task(_run_indexed_publication_refresh, req)
    return {"status": "started", "message": "OpenAlex publication refresh started in the background. This replaces publications only; run Enrich profiles after it finishes."}


@router.post("/indexed-departments/enrich-profiles")
def enrich_indexed_department_profiles(req: EnrichIndexedProfilesRequest, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    background_tasks.add_task(_run_indexed_profile_enrichment, req)
    return {"status": "started", "message": "Profile enrichment started in the background using profile text plus existing/OpenAlex publications."}


@router.delete("/indexed-departments")
def delete_indexed_department(req: DeleteIndexedDepartmentRequest, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Deletion requires explicit confirmation")
    return ProfessorService(session).delete_indexed_group(req.university, req.department)


@router.get("/scans/status")
def get_scan_status(_: User = Depends(require_admin)):
    from apps.backend.app.db import PROJECT_ROOT
    import json
    status_file = PROJECT_ROOT / "data" / "qa" / "job_status.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            return {"status": "idle", "message": "No active jobs"}
    return {"status": "idle", "message": "No active jobs"}


@router.post("/scans/run")
def run_scan(req: RunScanRequest, background_tasks: BackgroundTasks, _: User = Depends(require_admin)):
    from scripts.project.run_university_scan import ADAPTERS
    if req.adapter not in ADAPTERS:
        raise HTTPException(status_code=400, detail="Invalid adapter")
    
    background_tasks.add_task(
        execute_scan_task,
        adapter=req.adapter,
        enrich_profiles=req.enrich_profiles,
        enrich_publications=req.enrich_publications
    )
    return {"status": "started", "adapter": req.adapter}


@router.get("/scans", response_model=ListScansResponse)
def list_scans(_: User = Depends(require_admin)):
    return {"scans": AdminScanService().list_scans()}


@router.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def get_scan(scan_id: str, _: User = Depends(require_admin)):
    scan = AdminScanService().get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan artifact not found")
    return scan


@router.post("/scans/{scan_id}/import")
def import_scan(scan_id: str, _: User = Depends(require_admin), session: Session = Depends(get_session)):
    try:
        admin_service = AdminScanService()
        import_service = ImportService(session, admin_service)
        return import_service.import_scan(scan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
