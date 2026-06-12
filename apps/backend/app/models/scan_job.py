from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ScanJob(SQLModel, table=True):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        Index("ix_scan_jobs_status_created", "status", "created_at"),
        Index("ix_scan_jobs_type_status", "job_type", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    status: str = Field(default="queued", index=True)
    job_type: str = Field(default="agentic_onboarding", index=True)
    source: str = Field(default="admin", index=True)
    input_payload: dict = Field(default_factory=dict, sa_type=JSON)
    settings: dict = Field(default_factory=dict, sa_type=JSON)
    total_tasks: int = 0
    queued_tasks: int = 0
    running_tasks: int = 0
    succeeded_tasks: int = 0
    failed_tasks: int = 0
    canceled_tasks: int = 0
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None


class ScanTask(SQLModel, table=True):
    __tablename__ = "scan_tasks"
    __table_args__ = (
        Index("ix_scan_tasks_job_status", "scan_job_id", "status"),
        Index("ix_scan_tasks_status_lock", "status", "locked_until"),
        Index("ix_scan_tasks_priority_created", "priority", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_job_id: int = Field(foreign_key="scan_jobs.id", index=True)
    status: str = Field(default="queued", index=True)
    task_type: str = Field(default="department_agentic_scan", index=True)
    university: str = Field(index=True)
    department: str = Field(index=True)
    faculty_url: str
    input_payload: dict = Field(default_factory=dict, sa_type=JSON)
    attempt_count: int = 0
    max_attempts: int = 3
    priority: int = 0
    locked_by: Optional[str] = Field(default=None, index=True)
    locked_until: Optional[datetime] = Field(default=None, index=True)
    last_error: Optional[str] = None
    result_summary: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ScanResult(SQLModel, table=True):
    __tablename__ = "scan_results"
    __table_args__ = (
        Index("ix_scan_results_job_status", "scan_job_id", "status"),
        Index("ix_scan_results_task_status", "scan_task_id", "status"),
        Index("ix_scan_results_dedupe", "dedupe_key"),
        Index("ix_scan_results_import", "import_status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_job_id: int = Field(foreign_key="scan_jobs.id", index=True)
    scan_task_id: Optional[int] = Field(default=None, foreign_key="scan_tasks.id", index=True)
    status: str = Field(default="candidate", index=True)
    dedupe_key: Optional[str] = Field(default=None, index=True)
    professor_name: str = Field(index=True)
    university: str = Field(index=True)
    department: str = Field(index=True)
    title: Optional[str] = None
    email: Optional[str] = None
    profile_url: Optional[str] = None
    homepage_url: Optional[str] = None
    google_scholar_url: Optional[str] = None
    research_summary: Optional[str] = None
    research_tags: list[str] = Field(default_factory=list, sa_type=JSON)
    recruiting_signal: str = "unknown"
    source_confidence: float = 0.5
    source_urls: list[str] = Field(default_factory=list, sa_type=JSON)
    professor_payload: dict = Field(default_factory=dict, sa_type=JSON)
    publications_payload: list[dict] = Field(default_factory=list, sa_type=JSON)
    qa_issues: list[dict] = Field(default_factory=list, sa_type=JSON)
    import_status: str = Field(default="not_imported", index=True)
    imported_professor_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)


class ScanLog(SQLModel, table=True):
    __tablename__ = "scan_logs"
    __table_args__ = (
        Index("ix_scan_logs_job_created", "scan_job_id", "created_at"),
        Index("ix_scan_logs_task_created", "scan_task_id", "created_at"),
        Index("ix_scan_logs_level_created", "level", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    scan_job_id: int = Field(foreign_key="scan_jobs.id", index=True)
    scan_task_id: Optional[int] = Field(default=None, foreign_key="scan_tasks.id", index=True)
    level: str = Field(default="info", index=True)
    event_type: str = Field(index=True)
    message: str
    payload: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=utcnow, index=True)
