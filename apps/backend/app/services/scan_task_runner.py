from __future__ import annotations

import asyncio
from typing import Any

from sqlmodel import Session

from apps.backend.app.models.scan_job import ScanTask
from apps.backend.app.services.scan_job_service import ScanJobService


async def run_department_scan_task(task: ScanTask, session: Session, worker_id: str) -> None:
    """Run one durable department scan task and persist normalized candidates.

    This v1 runner wraps the existing agentic onboarding pipeline, but treats the
    JSON job file as temporary execution cache only. Durable task state, logs,
    candidate results, and errors are persisted through ScanJobService.
    """
    service = ScanJobService(session)
    service.append_scan_log(task.scan_job_id, task.id, "info", "crawl_started", f"Starting crawl for {task.faculty_url}")
    try:
        from apps.backend.app.services.agentic_onboarding_service import AgenticOnboardingService

        onboarding = AgenticOnboardingService()
        temp_job_id = onboarding.create_job(task.faculty_url, task.university, task.department)
        service.append_scan_log(task.scan_job_id, task.id, "info", "extraction_started", "Agentic extraction started", {"temp_job_id": temp_job_id})
        await onboarding.run_automatic_pipeline(temp_job_id)
        temp_job = onboarding.get_job(temp_job_id) or {}
        professors = temp_job.get("professors") if isinstance(temp_job.get("professors"), list) else []
        for professor in professors:
            if isinstance(professor, dict):
                professor.setdefault("university", task.university)
                professor.setdefault("department", task.department)
        saved = service.save_scan_results(task.scan_job_id, task.id, [p for p in professors if isinstance(p, dict)])
        summary: dict[str, Any] = {
            "professors_found": len(professors),
            "candidate_count": len(saved),
            "publications_found": sum(len(p.get("publications") or []) for p in professors if isinstance(p, dict)),
            "qa_issue_count": sum(len(r.qa_issues or []) for r in saved),
        }
        service.append_scan_log(task.scan_job_id, task.id, "info", "normalization_completed", "Candidates normalized", summary)
        service.mark_task_succeeded(task.id, summary)
    except asyncio.CancelledError:
        service.mark_task_failed(task.id, "Worker interrupted", retryable=True)
        raise
    except Exception as exc:
        service.mark_task_failed(task.id, str(exc), retryable=True)
