from sqlmodel import Session, select, distinct
from typing import List
from apps.backend.app.models.professor import Professor


class UniversityService:
    def __init__(self, session: Session):
        self.session = session

    def list_universities(self) -> List[str]:
        query = select(distinct(Professor.university)).order_by(Professor.university)
        universities = self.session.exec(query).all()
        return universities