from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class ScrapeRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    university: str
    department: Optional[str] = None
    adapter_name: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at: Optional[datetime] = None
    status: str  # e.g., "running", "completed", "failed"
    pages_attempted: int = Field(default=0)
    pages_successful: int = Field(default=0)
    records_created: int = Field(default=0)
    records_updated: int = Field(default=0)
    errors_json: Optional[str] = None  # JSON string of errors