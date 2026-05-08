from sqlmodel import Session
from apps.backend.app.models.student_profile import StudentProfile
from pydantic import BaseModel


class CreateStudentProfileRequest(BaseModel):
    background: str
    research_interests: str
    target_degree: str
    preferred_locations: str = None
    preferred_universities: str = None


class StudentProfileService:
    def __init__(self, session: Session):
        self.session = session

    def create_student_profile(self, request: CreateStudentProfileRequest) -> dict:
        profile = StudentProfile(
            background=request.background,
            research_interests=request.research_interests,
            target_degree=request.target_degree,
            preferred_locations=request.preferred_locations,
            preferred_universities=request.preferred_universities,
        )
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)

        return {
            "id": profile.id,
            "background": profile.background,
            "research_interests": profile.research_interests,
            "target_degree": profile.target_degree,
            "preferred_locations": profile.preferred_locations,
            "preferred_universities": profile.preferred_universities,
            "created_at": profile.created_at.isoformat(),
        }