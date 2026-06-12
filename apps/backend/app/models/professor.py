from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


class RecruitingSignal(str, Enum):
    positive = "positive"
    negative = "negative"
    unknown = "unknown"


class Professor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
    recruiting_signal: RecruitingSignal = Field(default=RecruitingSignal.unknown)
    recruiting_evidence_url: Optional[str] = None
    recruiting_evidence_text: Optional[str] = None
    source_confidence: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    extra: dict = Field(default_factory=dict, sa_type=JSON)

    # Relationship to publications
    publications: List["Publication"] = Relationship(back_populates="professor")


class Publication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    professor_id: int = Field(foreign_key="professor.id")
    title: str
    year: int
    venue: str
    abstract: Optional[str] = None
    url: Optional[str] = None
    source: str
    source_author_id: Optional[str] = None
    match_confidence: float

    # Back reference
    professor: Optional[Professor] = Relationship(back_populates="publications")