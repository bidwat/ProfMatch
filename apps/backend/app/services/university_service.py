from typing import List

from apps.backend.app.db import Database
from apps.backend.app.models.professor import PROFESSORS


class UniversityService:
    def __init__(self, db: Database):
        self.db = db

    def list_universities(self) -> List[str]:
        universities = {doc.get("university") for doc in self.db.collection(PROFESSORS).all() if doc.get("university")}
        return sorted(universities)
