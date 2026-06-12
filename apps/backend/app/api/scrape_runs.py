from fastapi import APIRouter, Depends, HTTPException
from apps.backend.app.db import Database, get_session
from apps.backend.app.services.scrape_run_service import ScrapeRunService
from pydantic import BaseModel
from typing import List, Optional


class ScrapeRunResponse(BaseModel):
    id: int
    university: str
    department: Optional[str]
    adapter_name: str
    started_at: str
    completed_at: Optional[str]
    status: str
    pages_attempted: int
    pages_successful: int
    records_created: int
    records_updated: int
    errors_json: Optional[str]


class ListScrapeRunsResponse(BaseModel):
    scrape_runs: List[ScrapeRunResponse]


router = APIRouter()


@router.get("/scrape-runs", response_model=ListScrapeRunsResponse)
def list_scrape_runs(db: Database = Depends(get_session)):
    service = ScrapeRunService(db)
    try:
        runs = service.list_scrape_runs()
        return {"scrape_runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")