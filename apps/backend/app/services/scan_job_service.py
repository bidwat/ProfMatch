from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable

from sqlalchemy import text
from sqlmodel import Session, select

from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.models.scan_job import ScanJob, ScanLog, ScanResult, ScanTask, utcnow

TERMINAL_TASK_STATUSES = {"succeeded", "failed", "canceled"}
ACTIVE_JOB_STATUSES = {"queued", "running"}


class ScanJobService:
    def __init__(self, session: Session):
        self.session = session

    def create_scan_job(
        self,
        *,
        items: list[dict[str, Any]],
        settings: dict[str, Any] | None = None,
        created_by_user_id: int | None = None,
        job_type: str = "agentic_onboarding",
        source: str = "admin",
    ) -> ScanJob:
        settings = settings or {}
        job = ScanJob(
            created_by_user_id=created_by_user_id,
            status="queued",
            job_type=job_type,
            source=source,
            input_payload={"items": items},
            settings=settings,
            total_tasks=len(items),
            queued_tasks=len(items),
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        self.append_scan_log(job.id, None, "info", "job_created", f"Created scan job with {len(items)} task(s)")
        self.create_scan_tasks(job.id, items, settings=settings)
        self.recalculate_job_progress(job.id)
        return self.get_scan_job(job.id) or job

    def create_scan_tasks(self, job_id: int, items: list[dict[str, Any]], *, settings: dict[str, Any] | None = None) -> list[ScanTask]:
        settings = settings or {}
        tasks: list[ScanTask] = []
        max_attempts = int(settings.get("max_attempts") or settings.get("SCAN_TASK_MAX_ATTEMPTS") or 3)
        for item in items:
            task = ScanTask(
                scan_job_id=job_id,
                university=str(item.get("university") or "").strip(),
                department=str(item.get("department") or "Computer Science").strip(),
                faculty_url=str(item.get("faculty_url") or item.get("url") or "").strip(),
                input_payload=item,
                max_attempts=max(1, min(10, max_attempts)),
                priority=int(item.get("priority") or 0),
            )
            self.session.add(task)
            tasks.append(task)
        self.session.commit()
        for task in tasks:
            self.session.refresh(task)
            self.append_scan_log(job_id, task.id, "info", "task_created", f"Queued {task.university} {task.department}")
        return tasks

    def get_scan_job(self, job_id: int) -> ScanJob | None:
        return self.session.get(ScanJob, job_id)

    def list_scan_jobs(self, *, limit: int = 50, offset: int = 0, status: str | None = None) -> list[ScanJob]:
        stmt = select(ScanJob).order_by(ScanJob.created_at.desc()).offset(offset).limit(limit)
        if status:
            stmt = select(ScanJob).where(ScanJob.status == status).order_by(ScanJob.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.exec(stmt).all())

    def list_scan_tasks(self, job_id: int) -> list[ScanTask]:
        return list(self.session.exec(select(ScanTask).where(ScanTask.scan_job_id == job_id).order_by(ScanTask.created_at)).all())

    def get_scan_task(self, task_id: int) -> ScanTask | None:
        return self.session.get(ScanTask, task_id)

    def claim_next_scan_task(self, worker_id: str, lease_seconds: int = 900) -> ScanTask | None:
        now = utcnow()
        dialect = self.session.get_bind().dialect.name if self.session.get_bind() is not None else "sqlite"
        if dialect == "postgresql":
            row = self.session.execute(
                text(
                    """
                    WITH next_task AS (
                      SELECT scan_tasks.id
                      FROM scan_tasks
                      JOIN scan_jobs ON scan_jobs.id = scan_tasks.scan_job_id
                      WHERE (
                          scan_tasks.status IN ('queued', 'retrying')
                          OR (scan_tasks.status = 'running' AND scan_tasks.locked_until < NOW())
                        )
                        AND scan_jobs.status NOT IN ('canceled', 'completed', 'completed_with_errors', 'failed')
                        AND (scan_tasks.locked_until IS NULL OR scan_tasks.locked_until < NOW())
                      ORDER BY scan_tasks.priority DESC, scan_tasks.created_at ASC
                      FOR UPDATE SKIP LOCKED
                      LIMIT 1
                    )
                    UPDATE scan_tasks
                    SET status = 'running', locked_by = :worker_id,
                        locked_until = NOW() + (:lease_seconds * INTERVAL '1 second'),
                        started_at = COALESCE(started_at, NOW()), updated_at = NOW(),
                        attempt_count = attempt_count + 1
                    WHERE id IN (SELECT id FROM next_task)
                    RETURNING id
                    """
                ),
                {"worker_id": worker_id, "lease_seconds": lease_seconds},
            ).first()
            self.session.commit()
            if not row:
                return None
            task = self.session.get(ScanTask, int(row[0]))
        else:
            task = self.session.exec(
                select(ScanTask)
                .join(ScanJob, ScanJob.id == ScanTask.scan_job_id)
                .where((ScanTask.status.in_(["queued", "retrying"])) | ((ScanTask.status == "running") & (ScanTask.locked_until < now)))
                .where(ScanJob.status.notin_(["canceled", "completed", "completed_with_errors", "failed"]))
                .order_by(ScanTask.priority.desc(), ScanTask.created_at)
            ).first()
            if not task:
                return None
            task.status = "running"
            task.locked_by = worker_id
            task.locked_until = now + timedelta(seconds=lease_seconds)
            task.started_at = task.started_at or now
            task.updated_at = now
            task.attempt_count += 1
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        if not task:
            return None
        job = self.get_scan_job(task.scan_job_id)
        if job and job.status == "queued":
            job.status = "running"
            job.started_at = job.started_at or now
            job.updated_at = now
            self.session.add(job)
            self.session.commit()
        self.append_scan_log(task.scan_job_id, task.id, "info", "task_claimed", f"Task claimed by {worker_id}")
        self.recalculate_job_progress(task.scan_job_id)
        return task

    def heartbeat_task(self, task_id: int, worker_id: str, lease_seconds: int = 900) -> bool:
        task = self.get_scan_task(task_id)
        if not task or task.locked_by != worker_id or task.status != "running":
            return False
        now = utcnow()
        task.locked_until = now + timedelta(seconds=lease_seconds)
        task.updated_at = now
        job = self.get_scan_job(task.scan_job_id)
        if job:
            job.heartbeat_at = now
            job.updated_at = now
            self.session.add(job)
        self.session.add(task)
        self.session.commit()
        return True

    def mark_task_succeeded(self, task_id: int, summary: dict[str, Any] | None = None) -> None:
        task = self.get_scan_task(task_id)
        if not task:
            return
        now = utcnow()
        task.status = "succeeded"
        task.result_summary = summary or {}
        task.locked_until = None
        task.finished_at = now
        task.updated_at = now
        self.session.add(task)
        self.session.commit()
        self.append_scan_log(task.scan_job_id, task.id, "info", "task_succeeded", "Task completed", summary or {})
        self.recalculate_job_progress(task.scan_job_id)

    def mark_task_failed(self, task_id: int, error: str, retryable: bool = True) -> None:
        task = self.get_scan_task(task_id)
        if not task:
            return
        now = utcnow()
        task.last_error = error[-4000:]
        if retryable and task.attempt_count < task.max_attempts:
            task.status = "retrying"
            event = "task_retrying"
        else:
            task.status = "failed"
            task.finished_at = now
            event = "task_failed"
        task.locked_until = None
        task.updated_at = now
        self.session.add(task)
        self.session.commit()
        self.append_scan_log(task.scan_job_id, task.id, "error", event, task.last_error)
        self.recalculate_job_progress(task.scan_job_id)

    def cancel_scan_job(self, job_id: int) -> ScanJob | None:
        job = self.get_scan_job(job_id)
        if not job:
            return None
        now = utcnow()
        job.status = "canceled"
        job.finished_at = now
        job.updated_at = now
        for task in self.list_scan_tasks(job_id):
            if task.status not in TERMINAL_TASK_STATUSES:
                task.status = "canceled"
                task.finished_at = now
                task.updated_at = now
                self.session.add(task)
        self.session.add(job)
        self.session.commit()
        self.append_scan_log(job_id, None, "warning", "job_canceled", "Scan job canceled")
        self.recalculate_job_progress(job_id)
        return self.get_scan_job(job_id)

    def recalculate_job_progress(self, job_id: int) -> ScanJob | None:
        job = self.get_scan_job(job_id)
        if not job:
            return None
        tasks = self.list_scan_tasks(job_id)
        total = len(tasks)
        counts = {status: sum(1 for task in tasks if task.status == status) for status in ["queued", "running", "succeeded", "failed", "canceled", "retrying"]}
        job.total_tasks = total
        job.queued_tasks = counts["queued"] + counts["retrying"]
        job.running_tasks = counts["running"]
        job.succeeded_tasks = counts["succeeded"]
        job.failed_tasks = counts["failed"]
        job.canceled_tasks = counts["canceled"]
        done = job.succeeded_tasks + job.failed_tasks + job.canceled_tasks
        job.progress_percent = round((done / total) * 100, 2) if total else 100.0
        now = utcnow()
        if job.status != "canceled":
            if total and done == total:
                job.status = "completed" if job.failed_tasks == 0 else "completed_with_errors"
                job.finished_at = job.finished_at or now
            elif job.running_tasks:
                job.status = "running"
                job.started_at = job.started_at or now
            elif job.queued_tasks:
                job.status = "queued"
        job.updated_at = now
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def append_scan_log(self, job_id: int, task_id: int | None, level: str, event_type: str, message: str, payload: dict[str, Any] | None = None) -> ScanLog:
        log = ScanLog(scan_job_id=job_id, scan_task_id=task_id, level=level, event_type=event_type, message=message, payload=payload or {})
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_scan_logs(self, job_id: int, *, limit: int = 200, offset: int = 0, level: str | None = None) -> list[ScanLog]:
        stmt = select(ScanLog).where(ScanLog.scan_job_id == job_id)
        if level:
            stmt = stmt.where(ScanLog.level == level)
        return list(self.session.exec(stmt.order_by(ScanLog.created_at.desc()).offset(offset).limit(limit)).all())

    def save_scan_results(self, job_id: int, task_id: int | None, results: Iterable[dict[str, Any]]) -> list[ScanResult]:
        saved: list[ScanResult] = []
        for item in results:
            name = str(item.get("name") or item.get("professor_name") or "").strip()
            if not name:
                continue
            university = str(item.get("university") or "").strip()
            department = str(item.get("department") or "").strip()
            dedupe_key = f"{name.lower()}::{university.lower()}"
            existing = self.session.exec(
                select(ScanResult).where(ScanResult.scan_job_id == job_id, ScanResult.dedupe_key == dedupe_key)
            ).first()
            if existing:
                continue
            publications = item.get("publications") if isinstance(item.get("publications"), list) else []
            urls = [u for u in [item.get("faculty_profile_url"), item.get("profile_url"), item.get("homepage")] if u]
            result = ScanResult(
                scan_job_id=job_id,
                scan_task_id=task_id,
                status="ready_for_review",
                dedupe_key=dedupe_key,
                professor_name=name,
                university=university,
                department=department,
                title=item.get("position") or item.get("title"),
                email=item.get("email"),
                profile_url=item.get("faculty_profile_url") or item.get("profile_url"),
                homepage_url=item.get("homepage") or item.get("homepage_url"),
                research_summary=item.get("ai_summary") or item.get("research_summary") or item.get("bio"),
                source_urls=urls,
                professor_payload=item,
                publications_payload=publications,
                qa_issues=self._qa_issues(item),
            )
            self.session.add(result)
            saved.append(result)
        self.session.commit()
        for result in saved:
            self.session.refresh(result)
        if saved:
            self.append_scan_log(job_id, task_id, "info", "result_saved", f"Saved {len(saved)} candidate result(s)", {"count": len(saved)})
        return saved

    def _qa_issues(self, item: dict[str, Any]) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        if not item.get("email"):
            issues.append({"severity": "warning", "code": "missing_email", "message": "Email missing"})
        if not (item.get("faculty_profile_url") or item.get("profile_url")):
            issues.append({"severity": "warning", "code": "missing_profile_url", "message": "Profile URL missing"})
        return issues

    def list_scan_results(self, job_id: int, *, status: str | None = None, limit: int = 200, offset: int = 0) -> list[ScanResult]:
        stmt = select(ScanResult).where(ScanResult.scan_job_id == job_id)
        if status:
            stmt = stmt.where(ScanResult.status == status)
        return list(self.session.exec(stmt.order_by(ScanResult.created_at.desc()).offset(offset).limit(limit)).all())

    def approve_scan_result(self, result_id: int) -> ScanResult | None:
        return self._set_result_status(result_id, "approved")

    def reject_scan_result(self, result_id: int) -> ScanResult | None:
        return self._set_result_status(result_id, "rejected")

    def _set_result_status(self, result_id: int, status: str) -> ScanResult | None:
        result = self.session.get(ScanResult, result_id)
        if not result:
            return None
        result.status = status
        result.updated_at = utcnow()
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        self.append_scan_log(result.scan_job_id, result.scan_task_id, "info", f"result_{status}", f"Result {result_id} marked {status}")
        return result

    def import_scan_result(self, result_id: int) -> ScanResult | None:
        result = self.session.get(ScanResult, result_id)
        if not result:
            return None
        if result.import_status == "imported":
            return result
        normalized_name = result.professor_name.lower().strip()
        existing = self.session.exec(
            select(Professor).where(Professor.normalized_name == normalized_name, Professor.university == result.university)
        ).first()
        if existing:
            professor = existing
            result.import_status = "skipped_duplicate"
            result.status = "duplicate"
        else:
            professor = Professor(
                name=result.professor_name,
                normalized_name=normalized_name,
                title=result.title,
                university=result.university,
                department=result.department,
                email=result.email,
                faculty_profile_url=result.profile_url,
                homepage_url=result.homepage_url,
                research_text=result.research_summary,
                research_summary=result.research_summary,
                recruiting_status=result.recruiting_signal,
                source_confidence=result.source_confidence,
                extra={"scan_result_id": result.id, "source_urls": result.source_urls},
            )
            self.session.add(professor)
            self.session.commit()
            self.session.refresh(professor)
            for pub in result.publications_payload or []:
                title = str(pub.get("title") or "").strip()
                if not title:
                    continue
                self.session.add(Publication(
                    professor_id=professor.id,
                    title=title,
                    year=int(pub.get("year") or 0),
                    venue=pub.get("venue") or "Unknown",
                    abstract=pub.get("abstract"),
                    url=pub.get("url"),
                    source=pub.get("source") or "scan_job",
                    match_confidence=float(pub.get("match_confidence") or 0.5),
                ))
            result.import_status = "imported"
            result.status = "imported"
        result.imported_professor_id = professor.id
        result.updated_at = utcnow()
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        self.append_scan_log(result.scan_job_id, result.scan_task_id, "info", "result_imported", f"Imported result {result.id}", {"professor_id": professor.id})
        return result
