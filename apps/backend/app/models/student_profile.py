from datetime import datetime
from typing import Optional

from pydantic import Field

from apps.backend.app.models.base import DocModel, utcnow

STUDENT_PROFILES = "student_profiles"


class StudentProfile(DocModel):
    background: str
    research_interests: str
    target_degree: str  # e.g., "MS", "PhD"
    preferred_locations: Optional[str] = None  # comma-separated or JSON
    preferred_universities: Optional[str] = None  # comma-separated or JSON
    created_at: datetime = Field(default_factory=utcnow)
