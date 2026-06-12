from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from apps.backend.app.models.base import DocModel, utcnow

PROFESSORS = "professors"
PUBLICATIONS = "publications"


class RecruitingSignal(str, Enum):
    positive = "positive"
    negative = "negative"
    unknown = "unknown"


class Professor(DocModel):
    name: str
    normalized_name: str
    title: Optional[str] = None
    university: str
    department: str
    email: Optional[str] = None
    faculty_profile_url: Optional[str] = None
    homepage_url: Optional[str] = None
    google_scholar_url: Optional[str] = None
    openalex_id: Optional[str] = None
    dblp_url: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    research_text: Optional[str] = None
    research_summary: Optional[str] = None
    recruiting_signal: str = RecruitingSignal.unknown.value
    recruiting_evidence_url: Optional[str] = None
    recruiting_evidence_text: Optional[str] = None
    source_confidence: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    extra: dict = Field(default_factory=dict)


class Publication(DocModel):
    professor_id: int
    title: str
    year: int = 0
    venue: str = "Unknown"
    abstract: Optional[str] = None
    url: Optional[str] = None
    source: str = "unknown"
    source_author_id: Optional[str] = None
    match_confidence: float = 0.0
