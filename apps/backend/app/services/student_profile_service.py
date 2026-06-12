from typing import Optional

from pydantic import BaseModel

from apps.backend.app.db import Database
from apps.backend.app.models.student_profile import STUDENT_PROFILES, StudentProfile


class CreateStudentProfileRequest(BaseModel):
    background: str
    research_interests: str
    target_degree: str
    preferred_locations: Optional[str] = None
    preferred_universities: Optional[str] = None


class StudentProfileService:
    def __init__(self, db: Database):
        self.db = db

    def create_student_profile(self, request: CreateStudentProfileRequest) -> dict:
        profile = StudentProfile(
            background=request.background,
            research_interests=request.research_interests,
            target_degree=request.target_degree,
            preferred_locations=request.preferred_locations,
            preferred_universities=request.preferred_universities,
        )
        profile.id = self.db.collection(STUDENT_PROFILES).add(profile.to_doc())

        return {
            "id": profile.id,
            "background": profile.background,
            "research_interests": profile.research_interests,
            "target_degree": profile.target_degree,
            "preferred_locations": profile.preferred_locations,
            "preferred_universities": profile.preferred_universities,
            "created_at": profile.created_at.isoformat(),
        }
