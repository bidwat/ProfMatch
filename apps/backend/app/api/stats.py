from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func, distinct
from apps.backend.app.db import get_session, DB_PATH
from apps.backend.app.models.professor import Professor, Publication


class UniversityStat(BaseModel):
    university: str
    professor_count: int
    publication_count: int


class ExplorerStatsResponse(BaseModel):
    database_path: str
    professor_count: int
    publication_count: int
    university_count: int
    professors_with_email: int
    professors_with_homepage: int
    professors_with_publications: int
    universities: list[UniversityStat]


router = APIRouter()


@router.get("/stats", response_model=ExplorerStatsResponse)
def explorer_stats(session: Session = Depends(get_session)):
    try:
        professor_count = session.exec(select(func.count(Professor.id))).one()
        publication_count = session.exec(select(func.count(Publication.id))).one()
        university_count = session.exec(select(func.count(distinct(Professor.university)))).one()
        professors_with_email = session.exec(
            select(func.count(Professor.id)).where(Professor.email.is_not(None), Professor.email != "")
        ).one()
        professors_with_homepage = session.exec(
            select(func.count(Professor.id)).where(Professor.homepage_url.is_not(None), Professor.homepage_url != "")
        ).one()
        professors_with_publications = session.exec(
            select(func.count(distinct(Publication.professor_id)))
        ).one()

        university_rows = session.exec(
            select(
                Professor.university,
                func.count(distinct(Professor.id)),
                func.count(Publication.id),
            )
            .outerjoin(Publication, Publication.professor_id == Professor.id)
            .group_by(Professor.university)
            .order_by(Professor.university)
        ).all()

        universities = [
            UniversityStat(
                university=row[0],
                professor_count=int(row[1] or 0),
                publication_count=int(row[2] or 0),
            )
            for row in university_rows
        ]

        return ExplorerStatsResponse(
            database_path=str(DB_PATH),
            professor_count=int(professor_count or 0),
            publication_count=int(publication_count or 0),
            university_count=int(university_count or 0),
            professors_with_email=int(professors_with_email or 0),
            professors_with_homepage=int(professors_with_homepage or 0),
            professors_with_publications=int(professors_with_publications or 0),
            universities=universities,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
