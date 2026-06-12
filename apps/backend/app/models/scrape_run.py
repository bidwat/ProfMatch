from datetime import datetime
from typing import Optional

from pydantic import Field

from apps.backend.app.models.base import DocModel, utcnow

SCRAPE_RUNS = "scrape_runs"


class ScrapeRun(DocModel):
    university: str
    department: Optional[str] = None
    adapter_name: str
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    pages_attempted: int = 0
    pages_successful: int = 0
    records_created: int = 0
    records_updated: int = 0
    errors_json: Optional[str] = None
