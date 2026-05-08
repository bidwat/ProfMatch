from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from apps.backend.app.db import get_session
from apps.backend.app.services.student_profile_service import StudentProfileService, CreateStudentProfileRequest
from pydantic import BaseModel


class CreateStudentProfileResponse(BaseModel):
    id: int
    background: str
    research_interests: str
    target_degree: str
    preferred_locations: Optional[str] = None
    preferred_universities: Optional[str] = None
    created_at: str


router = APIRouter()


@router.post("/student-profiles", response_model=CreateStudentProfileResponse)
def create_student_profile(request: CreateStudentProfileRequest, session: Session = Depends(get_session)):
    service = StudentProfileService(session)
    try:
        profile = service.create_student_profile(request)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")