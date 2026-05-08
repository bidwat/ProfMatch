from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class StudentProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    background: str
    research_interests: str
    target_degree: str  # e.g., "MS", "PhD"
    preferred_locations: Optional[str] = None  # comma-separated or JSON
    preferred_universities: Optional[str] = None  # comma-separated or JSON
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
