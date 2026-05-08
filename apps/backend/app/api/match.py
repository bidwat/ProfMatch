from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_session
from ..models.match import StudentProfile, MatchResponse, MatchScore
from ..models.professor import Professor
from ..services.match_service import MatchService

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
def match_professors(student: StudentProfile, session: Session = Depends(get_session)) -> MatchResponse:
    service = MatchService(session)
    result = service.find_matches_with_metadata(student)
    return MatchResponse(student=student, **result)