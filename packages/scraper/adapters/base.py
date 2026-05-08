from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..core.models import FetchResult, SourceArtifact
from ..core.run_manager import ScrapeRunManager, RunOutputs
from ..sources.catalog import get_seed_by_university
from ..sources.identifiers import hash_text, slugify


class UniversityAdapterProtocol(Protocol):
    university: str
    department: str
    faculty_roster_url: str
    adapter_name: str

    def scrape(self, *, run_id: str | None = None, output_root: Path | str = Path("."), fixture_path: Path | None = None, enrich_profiles: bool = True, enrich_publications: bool = False) -> RunOutputs: ...


@dataclass(slots=True)
class BaseUniversityAdapter:
    university: str
    department: str
    faculty_roster_url: str
    adapter_name: str
    roster_artifact_name: str = "roster.html"

    @property
    def university_slug(self) -> str:
        return slugify(self.university)

    @property
    def department_slug(self) -> str:
        return slugify(self.department)

    def build_fetch_result(self, *, run_id: str, body_text: str, output_root: Path | str) -> FetchResult:
        artifact = SourceArtifact(
            run_id=run_id,
            university_slug=self.university_slug,
            department_slug=self.department_slug,
            adapter_name=self.adapter_name,
            source_type="university_faculty_page",
            source_url=self.faculty_roster_url,
            artifact_name=self.roster_artifact_name,
            fetched_at="offline-fixture",
            status_code=200,
            content_type="text/html; charset=utf-8",
            content_hash=hash_text(body_text),
            byte_count=len(body_text.encode("utf-8")),
            notes="fixture-backed run",
        )
        return FetchResult(url=self.faculty_roster_url, body_text=body_text, source_artifact=artifact, fetched_at="offline-fixture")

    def scrape(self, *, run_id: str | None = None, output_root: Path | str = Path("."), fixture_path: Path | None = None, enrich_profiles: bool = True, enrich_publications: bool = False) -> RunOutputs:
        manager = ScrapeRunManager()
        return manager.run_adapter(
            self,
            run_id=run_id,
            output_root=output_root,
            fixture_path=fixture_path,
            enrich_profiles=enrich_profiles,
            enrich_publications=enrich_publications,
        )

    @classmethod
    def from_seed(cls, university_name: str, adapter_name: str | None = None) -> "BaseUniversityAdapter":
        seed = get_seed_by_university(university_name)
        return cls(seed.university, seed.department, seed.url, adapter_name or slugify(seed.university))
