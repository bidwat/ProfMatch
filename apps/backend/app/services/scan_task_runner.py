from __future__ import annotations

import asyncio

from apps.backend.app.db import Database
from apps.backend.app.models.scan_job import ScanTask
from apps.backend.app.services.durable_agentic_scan_service import DurableAgenticScanService
from apps.backend.app.services.scan_job_service import ScanJobService


async def run_department_scan_task(task: ScanTask, db: Database, worker_id: str) -> None:
    """Run one durable department scan task with all state in the database."""
    service = ScanJobService(db)
    try:
        summary = await DurableAgenticScanService(db).run_department_task(task)
        service.mark_task_succeeded(task.id, summary)
    except asyncio.CancelledError:
        service.mark_task_failed(task.id, "Worker interrupted", retryable=True)
        raise
    except Exception as exc:
        service.mark_task_failed(task.id, str(exc), retryable=True)
