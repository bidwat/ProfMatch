from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from apps.backend.app.db import get_session
from apps.backend.app.services.professor_service import ProfessorService
from apps.backend.app.services.university_service import UniversityService


class ListUniversitiesResponse(BaseModel):
    universities: List[str]


class DepartmentGroup(BaseModel):
    university: str
    department: str
    professor_count: int
    publication_count: int


class UniversitiesOverviewResponse(BaseModel):
    groups: List[DepartmentGroup] = Field(default_factory=list)


router = APIRouter()


@router.get("/universities", response_model=ListUniversitiesResponse)
def list_universities(session: Session = Depends(get_session)):
    service = UniversityService(session)
    try:
        universities = service.list_universities()
        return {"universities": universities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/universities/overview", response_model=UniversitiesOverviewResponse)
def universities_overview(session: Session = Depends(get_session)):
    """Public aggregate of indexed universities/departments with counts.

    Powers the public /universities directory and university/department
    pages (spec §22). Contains no sensitive data — only counts of already
    public professor profiles.
    """
    try:
        return {"groups": ProfessorService(session).list_indexed_groups()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
