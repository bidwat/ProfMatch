from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.backend.app.db import Database, database_kind, get_session, is_production_mode
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS


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


@router.get("/health")
def api_health():
    return {"status": "healthy"}


@router.get("/health/db")
def api_health_db(db: Database = Depends(get_session)):
    try:
        db_kind = database_kind()
        if is_production_mode() and db_kind != "firestore":
            raise HTTPException(status_code=500, detail="Production is not using Firestore; check Firebase credentials")
        return {
            "status": "healthy",
            "database": db_kind,
            "production": is_production_mode(),
            "professor_count": db.collection(PROFESSORS).count(),
            "publication_count": db.collection(PUBLICATIONS).count(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


@router.get("/stats", response_model=ExplorerStatsResponse)
def explorer_stats(db: Database = Depends(get_session)):
    try:
        professors = db.collection(PROFESSORS).all()
        publications = db.collection(PUBLICATIONS).all()

        pub_counts: dict[int, int] = {}
        for pub in publications:
            prof_id = pub.get("professor_id")
            if prof_id is not None:
                pub_counts[prof_id] = pub_counts.get(prof_id, 0) + 1

        university_stats: dict[str, dict] = {}
        for prof in professors:
            university = prof.get("university") or ""
            stat = university_stats.setdefault(university, {"university": university, "professor_count": 0, "publication_count": 0})
            stat["professor_count"] += 1
            stat["publication_count"] += pub_counts.get(prof.get("id"), 0)

        return ExplorerStatsResponse(
            database_path=database_kind(),
            professor_count=len(professors),
            publication_count=len(publications),
            university_count=len({p.get("university") for p in professors if p.get("university")}),
            professors_with_email=sum(1 for p in professors if (p.get("email") or "").strip()),
            professors_with_homepage=sum(1 for p in professors if (p.get("homepage_url") or "").strip()),
            professors_with_publications=len(pub_counts),
            universities=[UniversityStat(**university_stats[k]) for k in sorted(university_stats)],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
