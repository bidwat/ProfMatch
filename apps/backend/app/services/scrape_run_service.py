from sqlmodel import Session, select
from typing import List
from apps.backend.app.models.scrape_run import ScrapeRun


class ScrapeRunService:
    def __init__(self, session: Session):
        self.session = session

    def list_scrape_runs(self) -> List[dict]:
        query = select(ScrapeRun).order_by(ScrapeRun.started_at.desc())
        runs = self.session.exec(query).all()

        return [
            {
                "id": r.id,
                "university": r.university,
                "department": r.department,
                "adapter_name": r.adapter_name,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "pages_attempted": r.pages_attempted,
                "pages_successful": r.pages_successful,
                "records_created": r.records_created,
                "records_updated": r.records_updated,
                "errors_json": r.errors_json,
            }
            for r in runs
        ]