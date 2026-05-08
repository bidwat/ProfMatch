from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class StudentProfile(BaseModel):
    name: str = ""
    background: Optional[str] = None
    research_interests: str = Field(..., min_length=1)
    target_degree: str = "PhD"
    preferred_departments: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_universities: Optional[List[str]] = None
    limit: int = Field(default=5, ge=1, le=25)
    shortlist_limit: int = Field(default=50, ge=5, le=100)
    rerank: bool = False
    include_publication_evidence: bool = True
    max_abstracts_per_professor: int = Field(default=10, ge=1, le=10)

    @field_validator("research_interests")
    @classmethod
    def research_interests_must_have_non_whitespace_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("research_interests must contain non-whitespace text")
        return stripped


class PublicationEvidence(BaseModel):
    id: Optional[int] = None
    title: str
    year: Optional[int] = None
    url: Optional[str] = None
    venue: Optional[str] = None
    source: Optional[str] = None
    match_confidence: Optional[float] = None
    similarity_score: Optional[float] = None
    matched_terms: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    abstract_snippet: Optional[str] = None


class MatchEvidence(BaseModel):
    matched_terms: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    publications: List[PublicationEvidence] = Field(default_factory=list)
    recruiting_status: str = "unknown"
    recruiting_evidence_url: Optional[str] = None
    recruiting_evidence_text: Optional[str] = None
    risks: List[str] = Field(default_factory=list)


class MatchScore(BaseModel):
    professor_id: int
    professor_name: str = ""
    title: Optional[str] = None
    university: str = ""
    department: str = ""
    research_summary: Optional[str] = None
    professor_url: Optional[str] = None
    photo_url: Optional[str] = None
    photo_source_url: Optional[str] = None
    photo_confidence: Optional[float] = None
    total_score: float
    research_text_similarity: float
    recent_publication_similarity: float
    recruiting_signal_score: float
    department_title_relevance: float
    location_preference_fit: float
    fts_score: float = 0.0
    metadata_boost: float = 0.0
    explanation: str
    evidence: MatchEvidence = Field(default_factory=MatchEvidence)
    llm_rerank_score: Optional[float] = None
    llm_rerank_reason: Optional[str] = None
    risks_uncertainties: List[str] = Field(default_factory=list)
    suggested_outreach_angle: Optional[str] = None
    rerank_applied: bool = False


class MatchResponse(BaseModel):
    student: StudentProfile
    matches: List[MatchScore]
    shortlist_size: int = 0
    rerank_applied: bool = False
    rerank_model: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
