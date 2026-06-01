from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func, distinct
from apps.backend.app.db import get_session, DATABASE_URL, DB_PATH, is_production_mode
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


def _db_kind() -> str:
    if DATABASE_URL.startswith("sqlite"):
        return "sqlite"
    if DATABASE_URL.startswith("postgresql+psycopg"):
        return "postgres"
    return "other"


@router.get("/health")
def api_health():
    return {"status": "healthy"}


@router.get("/health/db")
def api_health_db(session: Session = Depends(get_session)):
    try:
        professor_count = int(session.exec(select(func.count(Professor.id))).one() or 0)
        publication_count = int(session.exec(select(func.count(Publication.id))).one() or 0)
        db_kind = _db_kind()
        if is_production_mode() and db_kind == "sqlite":
            raise HTTPException(status_code=500, detail="Production is using SQLite; expected Postgres")
        return {
            "status": "healthy",
            "database": db_kind,
            "production": is_production_mode(),
            "professor_count": professor_count,
            "publication_count": publication_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


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
            database_path=str(DB_PATH) if DB_PATH else DATABASE_URL.split('@')[-1],
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
