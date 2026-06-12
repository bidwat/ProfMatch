from __future__ import annotations

import threading
from datetime import timedelta
from typing import Any, Iterable

from apps.backend.app.db import Database
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication
from apps.backend.app.models.scan_job import (
    SCAN_JOBS,
    SCAN_LOGS,
    SCAN_RESULTS,
    SCAN_TASKS,
    ScanJob,
    ScanLog,
    ScanResult,
    ScanTask,
    utcnow,
)

TERMINAL_TASK_STATUSES = {"succeeded", "failed", "canceled"}
ACTIVE_JOB_STATUSES = {"queued", "running"}

# Task claiming is serialized per process. The deployment runs a single scan
# worker, so this is sufficient; multi-worker deployments would need a
# Firestore transaction here instead.
_claim_lock = threading.Lock()


class ScanJobService:
    def __init__(self, db: Database):
        self.db = db
        self.jobs = db.collection(SCAN_JOBS)
        self.tasks = db.collection(SCAN_TASKS)
        self.results = db.collection(SCAN_RESULTS)
        self.logs = db.collection(SCAN_LOGS)

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
        job.id = self.jobs.add(job.to_doc())
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
            task.id = self.tasks.add(task.to_doc())
            tasks.append(task)
            self.append_scan_log(job_id, task.id, "info", "task_created", f"Queued {task.university} {task.department}")
        return tasks

    def get_scan_job(self, job_id: int) -> ScanJob | None:
        doc = self.jobs.get(job_id)
        return ScanJob.from_doc(doc) if doc else None

    def list_scan_jobs(self, *, limit: int = 50, offset: int = 0, status: str | None = None) -> list[ScanJob]:
        docs = self.jobs.find(status=status) if status else self.jobs.all()
        jobs = [ScanJob.from_doc(doc) for doc in docs]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[offset:offset + limit]

    def list_scan_tasks(self, job_id: int) -> list[ScanTask]:
        tasks = [ScanTask.from_doc(doc) for doc in self.tasks.find(scan_job_id=job_id)]
        tasks.sort(key=lambda t: t.created_at)
        return tasks

    def get_scan_task(self, task_id: int) -> ScanTask | None:
        doc = self.tasks.get(task_id)
        return ScanTask.from_doc(doc) if doc else None

    def claim_next_scan_task(self, worker_id: str, lease_seconds: int = 900) -> ScanTask | None:
        now = utcnow()
        with _claim_lock:
            active_job_ids = {
                doc["id"]
                for doc in self.jobs.all()
                if doc.get("status") not in {"canceled", "completed", "completed_with_errors", "failed"}
            }
            candidates = []
            for doc in self.tasks.all():
                if doc.get("scan_job_id") not in active_job_ids:
                    continue
                status = doc.get("status")
                locked_until = doc.get("locked_until")
                claimable = status in {"queued", "retrying"} or (
                    status == "running" and locked_until is not None and locked_until < now
                )
                if claimable:
                    candidates.append(ScanTask.from_doc(doc))
            if not candidates:
                return None
            candidates.sort(key=lambda t: (-t.priority, t.created_at))
            task = candidates[0]
            task.status = "running"
            task.locked_by = worker_id
            task.locked_until = now + timedelta(seconds=lease_seconds)
            task.started_at = task.started_at or now
            task.updated_at = now
            task.attempt_count += 1
            self.tasks.set(task.id, task.to_doc())

        job = self.get_scan_job(task.scan_job_id)
        if job and job.status == "queued":
            self.jobs.update(job.id, {"status": "running", "started_at": job.started_at or now, "updated_at": now})
        self.append_scan_log(task.scan_job_id, task.id, "info", "task_claimed", f"Task claimed by {worker_id}")
        self.recalculate_job_progress(task.scan_job_id)
        return task

    def heartbeat_task(self, task_id: int, worker_id: str, lease_seconds: int = 900) -> bool:
        task = self.get_scan_task(task_id)
        if not task or task.locked_by != worker_id or task.status != "running":
            return False
        now = utcnow()
        self.tasks.update(task_id, {"locked_until": now + timedelta(seconds=lease_seconds), "updated_at": now})
        if self.jobs.get(task.scan_job_id):
            self.jobs.update(task.scan_job_id, {"heartbeat_at": now, "updated_at": now})
        return True

    def mark_task_succeeded(self, task_id: int, summary: dict[str, Any] | None = None) -> None:
        task = self.get_scan_task(task_id)
        if not task:
            return
        now = utcnow()
        self.tasks.update(task_id, {
            "status": "succeeded",
            "result_summary": summary or {},
            "locked_until": None,
            "finished_at": now,
            "updated_at": now,
        })
        self.append_scan_log(task.scan_job_id, task.id, "info", "task_succeeded", "Task completed", summary or {})
        self.recalculate_job_progress(task.scan_job_id)

    def mark_task_failed(self, task_id: int, error: str, retryable: bool = True) -> None:
        task = self.get_scan_task(task_id)
        if not task:
            return
        now = utcnow()
        last_error = error[-4000:]
        patch: dict[str, Any] = {"last_error": last_error, "locked_until": None, "updated_at": now}
        if retryable and task.attempt_count < task.max_attempts:
            patch["status"] = "retrying"
            event = "task_retrying"
        else:
            patch["status"] = "failed"
            patch["finished_at"] = now
            event = "task_failed"
        self.tasks.update(task_id, patch)
        self.append_scan_log(task.scan_job_id, task.id, "error", event, last_error)
        self.recalculate_job_progress(task.scan_job_id)

    def cancel_scan_job(self, job_id: int) -> ScanJob | None:
        job = self.get_scan_job(job_id)
        if not job:
            return None
        now = utcnow()
        self.jobs.update(job_id, {"status": "canceled", "finished_at": now, "updated_at": now})
        for task in self.list_scan_tasks(job_id):
            if task.status not in TERMINAL_TASK_STATUSES:
                self.tasks.update(task.id, {"status": "canceled", "finished_at": now, "updated_at": now})
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
        patch: dict[str, Any] = {
            "total_tasks": total,
            "queued_tasks": counts["queued"] + counts["retrying"],
            "running_tasks": counts["running"],
            "succeeded_tasks": counts["succeeded"],
            "failed_tasks": counts["failed"],
            "canceled_tasks": counts["canceled"],
        }
        done = counts["succeeded"] + counts["failed"] + counts["canceled"]
        patch["progress_percent"] = round((done / total) * 100, 2) if total else 100.0
        now = utcnow()
        if job.status != "canceled":
            if total and done == total:
                patch["status"] = "completed" if counts["failed"] == 0 else "completed_with_errors"
                patch["finished_at"] = job.finished_at or now
            elif counts["running"]:
                patch["status"] = "running"
                patch["started_at"] = job.started_at or now
            elif patch["queued_tasks"]:
                patch["status"] = "queued"
        patch["updated_at"] = now
        self.jobs.update(job_id, patch)
        return self.get_scan_job(job_id)

    def append_scan_log(self, job_id: int, task_id: int | None, level: str, event_type: str, message: str, payload: dict[str, Any] | None = None) -> ScanLog:
        log = ScanLog(scan_job_id=job_id, scan_task_id=task_id, level=level, event_type=event_type, message=message, payload=payload or {})
        log.id = self.logs.add(log.to_doc())
        return log

    def list_scan_logs(self, job_id: int, *, limit: int = 200, offset: int = 0, level: str | None = None) -> list[ScanLog]:
        docs = self.logs.find(scan_job_id=job_id, level=level) if level else self.logs.find(scan_job_id=job_id)
        logs = [ScanLog.from_doc(doc) for doc in docs]
        logs.sort(key=lambda log: log.created_at, reverse=True)
        return logs[offset:offset + limit]

    def save_scan_results(self, job_id: int, task_id: int | None, results: Iterable[dict[str, Any]]) -> list[ScanResult]:
        existing_keys = {doc.get("dedupe_key") for doc in self.results.find(scan_job_id=job_id)}
        saved: list[ScanResult] = []
        for item in results:
            name = str(item.get("name") or item.get("professor_name") or "").strip()
            if not name:
                continue
            university = str(item.get("university") or "").strip()
            department = str(item.get("department") or "").strip()
            dedupe_key = f"{name.lower()}::{university.lower()}"
            if dedupe_key in existing_keys:
                continue
            existing_keys.add(dedupe_key)
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
            result.id = self.results.add(result.to_doc())
            saved.append(result)
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
        docs = self.results.find(scan_job_id=job_id, status=status) if status else self.results.find(scan_job_id=job_id)
        results = [ScanResult.from_doc(doc) for doc in docs]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[offset:offset + limit]

    def get_scan_result(self, result_id: int) -> ScanResult | None:
        doc = self.results.get(result_id)
        return ScanResult.from_doc(doc) if doc else None

    def save_scan_result(self, result: ScanResult) -> ScanResult:
        self.results.set(result.id, result.to_doc())
        return result

    def approve_scan_result(self, result_id: int) -> ScanResult | None:
        return self._set_result_status(result_id, "approved")

    def reject_scan_result(self, result_id: int) -> ScanResult | None:
        return self._set_result_status(result_id, "rejected")

    def _set_result_status(self, result_id: int, status: str) -> ScanResult | None:
        result = self.get_scan_result(result_id)
        if not result:
            return None
        self.results.update(result_id, {"status": status, "updated_at": utcnow()})
        self.append_scan_log(result.scan_job_id, result.scan_task_id, "info", f"result_{status}", f"Result {result_id} marked {status}")
        return self.get_scan_result(result_id)

    def import_scan_result(self, result_id: int) -> ScanResult | None:
        result = self.get_scan_result(result_id)
        if not result:
            return None
        if result.import_status == "imported":
            return result
        professors = self.db.collection(PROFESSORS)
        publications = self.db.collection(PUBLICATIONS)
        normalized_name = result.professor_name.lower().strip()
        existing_doc = next(
            (doc for doc in professors.find(normalized_name=normalized_name) if doc.get("university") == result.university),
            None,
        )
        if existing_doc:
            professor_id = existing_doc["id"]
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
                recruiting_signal=result.recruiting_signal,
                source_confidence=result.source_confidence,
                extra={"scan_result_id": result.id, "source_urls": result.source_urls},
            )
            professor_id = professors.add(professor.to_doc())
            for pub in result.publications_payload or []:
                title = str(pub.get("title") or "").strip()
                if not title:
                    continue
                publications.add(Publication(
                    professor_id=professor_id,
                    title=title,
                    year=int(pub.get("year") or 0),
                    venue=pub.get("venue") or "Unknown",
                    abstract=pub.get("abstract"),
                    url=pub.get("url"),
                    source=pub.get("source") or "scan_job",
                    match_confidence=float(pub.get("match_confidence") or 0.5),
                ).to_doc())
            result.import_status = "imported"
            result.status = "imported"
        result.imported_professor_id = professor_id
        result.updated_at = utcnow()
        self.results.set(result.id, result.to_doc())
        self.append_scan_log(result.scan_job_id, result.scan_task_id, "info", "result_imported", f"Imported result {result.id}", {"professor_id": professor_id})
        return result
