from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from apps.backend.app.db import get_session
from apps.backend.app.services.university_service import UniversityService
from pydantic import BaseModel
from typing import List


class ListUniversitiesResponse(BaseModel):
    universities: List[str]


router = APIRouter()


@router.get("/universities", response_model=ListUniversitiesResponse)
def list_universities(session: Session = Depends(get_session)):
    service = UniversityService(session)
    try:
        universities = service.list_universities()
        return {"universities": universities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")