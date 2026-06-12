"""End-to-end check of the Crawl4AI-backed durable scan pipeline.

Network edges (Crawl4AI crawl, LLM extraction, OpenAlex enrichment) are
mocked; everything between them — job/task state, candidate persistence,
QA issues, summaries, approval, and import into the canonical tables —
runs for real against the database.
"""

import asyncio

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from apps.backend.app.models import auth as auth_models  # noqa: F401 - register users table for scan_jobs FK
from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.services.durable_agentic_scan_service import DurableAgenticScanService
from apps.backend.app.services.scan_job_service import ScanJobService


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'scanflow.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


ROSTER_MD = "# Faculty\n- [Dr. Ada Lovelace](/people/ada)\n"
PROFILE_MD = "# Ada Lovelace\nProfessor of Computing. Works on analytical engines.\n"


def test_durable_scan_pipeline_from_crawl_to_import(session, monkeypatch):
    jobs = ScanJobService(session)
    job = jobs.create_scan_job(
        items=[{"university": "Test University", "department": "Computer Science", "faculty_url": "https://example.edu/cs/people"}],
        settings={},
    )
    task = jobs.claim_next_scan_task("test-worker", lease_seconds=60)
    assert task is not None

    async def fake_crawl(self, url: str) -> str:
        return ROSTER_MD if "people" in url and not url.endswith("/ada") else PROFILE_MD

    def fake_llm(prompt, is_json=True):
        if '"professors"' in prompt:
            return {"professors": [{"name": "Ada Lovelace", "profile_url": "/people/ada"}]}
        if "Extract professor profile fields" in prompt:
            return {
                "name": "Ada Lovelace", "position": "Professor", "email": "ada@example.edu",
                "homepage": None, "photo": None, "bio": "Works on analytical engines and computation.",
            }
        return "Ada Lovelace researches analytical engines, grounded in recent publications."

    class FakeEnrichment:
        matched = True
        records = [{"title": "Notes on the Analytical Engine", "year": 2025, "venue": "Computation Letters", "abstract": "Engines.", "url": None, "source_author_id": "A1", "match_confidence": 0.9}]
        confidence = 0.9
        source_author_id = "A1"
        source_url = "https://openalex.org/A1"
        reason = None

    monkeypatch.setattr(DurableAgenticScanService, "_crawl_url", fake_crawl)
    monkeypatch.setattr("apps.backend.app.services.durable_agentic_scan_service._call_llm", fake_llm)
    monkeypatch.setattr(
        "apps.backend.app.services.openalex_publication_service.OpenAlexEnricher.enrich_by_author_name_and_institution",
        lambda self, name, institution_name=None, max_publications=10: FakeEnrichment(),
    )

    service = DurableAgenticScanService(session)
    summary = asyncio.run(service.run_department_task(task))
    jobs.mark_task_succeeded(task.id, summary)

    assert summary["candidate_count"] == 1
    assert summary["publications_found"] == 1
    refreshed_job = jobs.get_scan_job(job.id)
    assert refreshed_job.status == "completed"

    results = jobs.list_scan_results(job.id)
    assert len(results) == 1
    candidate = results[0]
    assert candidate.professor_name == "Ada Lovelace"
    assert candidate.publications_payload[0]["title"] == "Notes on the Analytical Engine"
    assert "analytical engines" in (candidate.research_summary or "").lower()

    # Admin approves and imports the candidate into the canonical tables.
    jobs.approve_scan_result(candidate.id)
    imported = jobs.import_scan_result(candidate.id)
    assert imported.import_status == "imported"
    professor = session.exec(select(Professor).where(Professor.normalized_name == "ada lovelace")).first()
    assert professor is not None and professor.university == "Test University"
    publications = session.exec(select(Publication).where(Publication.professor_id == professor.id)).all()
    assert len(publications) == 1
