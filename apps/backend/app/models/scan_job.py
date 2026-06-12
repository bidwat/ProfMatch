from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from apps.backend.app.models.base import DocModel, utcnow

SCAN_JOBS = "scan_jobs"
SCAN_TASKS = "scan_tasks"
SCAN_RESULTS = "scan_results"
SCAN_LOGS = "scan_logs"

__all__ = [
    "ScanJob",
    "ScanTask",
    "ScanResult",
    "ScanLog",
    "utcnow",
    "SCAN_JOBS",
    "SCAN_TASKS",
    "SCAN_RESULTS",
    "SCAN_LOGS",
]


class ScanJob(DocModel):
    created_by_user_id: Optional[int] = None
    status: str = "queued"
    job_type: str = "agentic_onboarding"
    source: str = "admin"
    input_payload: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    succeeded_tasks: int = 0
    failed_tasks: int = 0
    canceled_tasks: int = 0
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None


class ScanTask(DocModel):
    scan_job_id: int
    status: str = "queued"
    task_type: str = "department_agentic_scan"
    university: str
    department: str
    faculty_url: str
    input_payload: dict = Field(default_factory=dict)
    attempt_count: int = 0
    max_attempts: int = 3
    priority: int = 0
    locked_by: Optional[str] = None
    locked_until: Optional[datetime] = None
    last_error: Optional[str] = None
    result_summary: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ScanResult(DocModel):
    scan_job_id: int
    scan_task_id: Optional[int] = None
    status: str = "candidate"
    dedupe_key: Optional[str] = None
    professor_name: str
    university: str
    department: str
    title: Optional[str] = None
    email: Optional[str] = None
    profile_url: Optional[str] = None
    homepage_url: Optional[str] = None
    google_scholar_url: Optional[str] = None
    research_summary: Optional[str] = None
    research_tags: list[str] = Field(default_factory=list)
    recruiting_signal: str = "unknown"
    source_confidence: float = 0.5
    source_urls: list[str] = Field(default_factory=list)
    professor_payload: dict = Field(default_factory=dict)
    publications_payload: list[dict] = Field(default_factory=list)
    qa_issues: list[dict] = Field(default_factory=list)
    import_status: str = "not_imported"
    imported_professor_id: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ScanLog(DocModel):
    scan_job_id: int
    scan_task_id: Optional[int] = None
    level: str = "info"
    event_type: str = "event"
    message: str = ""
    payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
