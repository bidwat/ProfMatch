from typing import List

from apps.backend.app.db import Database
from apps.backend.app.models.scrape_run import SCRAPE_RUNS, ScrapeRun


class ScrapeRunService:
    def __init__(self, db: Database):
        self.db = db

    def list_scrape_runs(self) -> List[dict]:
        runs = [ScrapeRun.from_doc(doc) for doc in self.db.collection(SCRAPE_RUNS).all()]
        runs.sort(key=lambda r: r.started_at, reverse=True)

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
