from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..db import Database, get_session
from ..models.match import StudentProfile, MatchResponse, MatchScore
from ..models.professor import Professor
from ..services.match_service import MatchService

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
def match_professors(student: StudentProfile, db: Database = Depends(get_session)) -> MatchResponse:
    service = MatchService(db)
    result = service.find_matches_with_metadata(student)
    return MatchResponse(student=student, **result)