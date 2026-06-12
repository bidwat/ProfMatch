from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Any
from apps.backend.app.db import Database, get_session
from apps.backend.app.services.professor_service import ProfessorService
from pydantic import BaseModel, Field
from enum import Enum


class RecruitingSignal(str, Enum):
    positive = "positive"
    negative = "negative"
    unknown = "unknown"


class ProfessorSummary(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    university: str
    department: str
    research_summary: Optional[str] = None
    recruiting_signal: str  # Using str since enum value
    source_confidence: float
    publication_count: int = 0
    tags: list[str] = Field(default_factory=list)
    profile_display_status: Optional[str] = None
    profile_text_source_url: Optional[str] = None
    profile_text_confidence: Optional[float] = None
    photo_url: Optional[str] = None
    photo_source_url: Optional[str] = None
    photo_confidence: Optional[float] = None


class ListProfessorsResponse(BaseModel):
    professors: list[ProfessorSummary]
    total: int
    page: int
    limit: int
    next_cursor: Optional[str] = None


class ProfessorFacetsResponse(BaseModel):
    tags: list[str] = Field(default_factory=list)
    universities: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    recruiting_signals: list[str] = Field(default_factory=list)


class PublicationResponse(BaseModel):
    id: int
    title: str
    year: int
    venue: str
    abstract: Optional[str]
    url: Optional[str]
    source: str
    source_author_id: Optional[str]
    match_confidence: float


class ProfessorDetail(BaseModel):
    id: int
    name: str
    normalized_name: str
    title: Optional[str] = None
    university: str
    department: str
    email: Optional[str]
    faculty_profile_url: Optional[str]
    homepage_url: Optional[str]
    google_scholar_url: Optional[str]
    openalex_id: Optional[str]
    dblp_url: Optional[str]
    semantic_scholar_id: Optional[str]
    research_text: Optional[str] = None
    research_summary: Optional[str] = None
    recruiting_signal: str
    recruiting_evidence_url: Optional[str]
    recruiting_evidence_text: Optional[str]
    source_confidence: float
    created_at: str
    updated_at: str
    photo_url: Optional[str] = None
    photo_source_url: Optional[str] = None
    photo_confidence: Optional[float] = None
    photo_license_note: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GetProfessorResponse(BaseModel):
    professor: ProfessorDetail
    publications: list[PublicationResponse]


router = APIRouter()


@router.get("/professors/facets", response_model=ProfessorFacetsResponse)
def professor_facets(db: Database = Depends(get_session)):
    service = ProfessorService(db)
    try:
        return service.list_facets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/professors", response_model=ListProfessorsResponse)
def list_professors(
    q: Optional[str] = Query(None, description="FTS search on name, title, research_text"),
    university: list[str] | None = Query(None, description="Exact university match; repeat for multiple"),
    department: list[str] | None = Query(None, description="Exact department match; repeat for multiple"),
    title: Optional[str] = Query(None, description="Exact title match"),
    tag: list[str] | None = Query(None, description="Exact tag match from professor metadata; repeat for multiple"),
    recruiting_signal: Optional[RecruitingSignal] = Query(None, description="Recruiting status"),
    sort: str = Query("name-asc", pattern="^(name|university|recruiting)-(asc|desc)$"),
    cursor: Optional[str] = Query(None, description="Opaque cursor for lazy loading"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Database = Depends(get_session),
):
    service = ProfessorService(db)
    try:
        return service.list_professors(q=q, university=university, department=department, title=title, tag=tag, recruiting_signal=recruiting_signal.value if recruiting_signal else None, sort=sort, cursor=cursor, page=page, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/professors/{professor_id}", response_model=GetProfessorResponse)
def get_professor(professor_id: int, db: Database = Depends(get_session)):
    if professor_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid professor ID")

    service = ProfessorService(db)
    try:
        result = service.get_professor_by_id(professor_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Professor not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")