from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence
from uuid import uuid4

from .deduper import DuplicateCandidateDetector
from .enrichers import DBLPEnricher, OpenAlexEnricher, SemanticScholarEnricher
from .fetcher import SafeFetcher
from .models import (
    EnrichmentResult,
    NormalizedProfessorRecord,
    NormalizedPublicationRecord,
    PublicationCandidate,
    ScrapeRunRecord,
    ValidationIssue,
)
from .normalizer import ProfessorNormalizer, PublicationNormalizer
from .parser import FacultyRosterParser
from .validator import RecordValidator
from .writer import ArtifactWriter


@dataclass(slots=True)
class RunOutputs:
    run_record: ScrapeRunRecord
    raw_path: Path
    processed_paths: dict[str, Path]
    professor_records: List[NormalizedProfessorRecord]
    publication_records: List[NormalizedPublicationRecord]
    validation_issues: List[ValidationIssue]
    duplicates: List[dict]


class ScrapeRunManager:
    def __init__(
        self,
        *,
        fetcher: Optional[SafeFetcher] = None,
        parser: Optional[FacultyRosterParser] = None,
        normalizer: Optional[ProfessorNormalizer] = None,
        publication_normalizer: Optional[PublicationNormalizer] = None,
        validator: Optional[RecordValidator] = None,
        deduper: Optional[DuplicateCandidateDetector] = None,
        writer: Optional[ArtifactWriter] = None,
        publication_enrichers: Optional[Sequence[object]] = None,
    ) -> None:
        self.fetcher = fetcher or SafeFetcher()
        self.parser = parser or FacultyRosterParser()
        self.normalizer = normalizer or ProfessorNormalizer()
        self.publication_normalizer = publication_normalizer or PublicationNormalizer()
        self.validator = validator or RecordValidator()
        self.deduper = deduper or DuplicateCandidateDetector()
        self.writer = writer or ArtifactWriter()
        self.publication_enrichers = list(publication_enrichers) if publication_enrichers is not None else [
            OpenAlexEnricher(),
            DBLPEnricher(),
            SemanticScholarEnricher(),
        ]

    def generate_run_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]

    def _enrich_publications_for_professor(
        self,
        professor: NormalizedProfessorRecord,
        *,
        max_publications_per_source: int = 3,
    ) -> tuple[List[NormalizedPublicationRecord], List[dict]]:
        publication_records: List[NormalizedPublicationRecord] = []
        enrichment_audit: List[dict] = []

        for enricher in self.publication_enrichers:
            enricher_name = getattr(enricher, "source_name", enricher.__class__.__name__.lower())
            if not hasattr(enricher, "enrich_by_author_name"):
                enrichment_audit.append(
                    {
                        "source": enricher_name,
                        "matched": False,
                        "reason": "Enricher missing enrich_by_author_name",
                        "confidence": 0.0,
                    }
                )
                continue

            result: EnrichmentResult = enricher.enrich_by_author_name(
                professor.name,
                max_publications=max_publications_per_source,
            )
            enrichment_audit.append(result.to_dict())

            for record in result.records:
                try:
                    candidate = PublicationCandidate(
                        title=record.get("title") or "",
                        year=int(record.get("year") or 0),
                        venue=record.get("venue") or "",
                        url=record.get("url") or "",
                        source=record.get("source") or enricher_name,
                        source_author_id=record.get("source_author_id") or result.source_author_id or "",
                        match_confidence=float(record.get("match_confidence") or result.confidence or 0.0),
                        abstract=record.get("abstract"),
                        citation_count=record.get("citation_count"),
                        authors=list(record.get("authors") or []),
                        openalex_id=record.get("openalex_id"),
                        dblp_key=record.get("dblp_key"),
                        semantic_scholar_id=record.get("semantic_scholar_id"),
                        extra={
                            "professor_name": professor.name,
                            "professor_normalized_name": professor.normalized_name,
                            "professor_university": professor.university,
                            "professor_department": professor.department,
                            "professor_profile_url": professor.faculty_profile_url,
                        },
                    )
                except Exception:
                    continue
                publication_records.append(self.publication_normalizer.normalize(candidate))

        deduped: List[NormalizedPublicationRecord] = []
        seen: set[tuple[str, int, str]] = set()
        for record in publication_records:
            key = (record.title.strip().lower(), int(record.year or 0), record.source)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(record)

        return deduped, enrichment_audit

    def run_adapter(
        self,
        adapter,
        *,
        run_id: Optional[str] = None,
        output_root: Path | str = Path("."),
        fixture_path: Path | None = None,
        enrich_profiles: bool = True,
        enrich_publications: Optional[bool] = None,
    ) -> RunOutputs:
        run_id = run_id or self.generate_run_id()
        output_root = Path(output_root)
        # Writer root is per-run so tests can isolate artifacts in temp dirs and
        # CLI callers can choose the project/output root explicitly.
        self.writer = ArtifactWriter(output_root)
        started_at = datetime.now(timezone.utc).isoformat()
        if fixture_path is not None:
            body_text = fixture_path.read_text(encoding="utf-8")
            fetch_result = adapter.build_fetch_result(run_id=run_id, body_text=body_text, output_root=output_root)
        else:
            fetch_result = self.fetcher.fetch(
                adapter.faculty_roster_url,
                run_id=run_id,
                university=adapter.university,
                department=adapter.department,
                adapter_name=adapter.adapter_name,
                artifact_name=adapter.roster_artifact_name,
                source_type="university_faculty_page",
            )
        raw_path = self.writer.write_fetch_result(fetch_result)
        candidates = self.parser.parse_roster_html(
            fetch_result.body_text,
            source_url=fetch_result.url,
            university=adapter.university,
            department=adapter.department,
        )

        # Deduplicate candidates strictly by URL/name to prevent CSS selector overlap issues
        unique_candidates = {}
        for c in candidates:
            key = c.faculty_profile_url or c.name
            if key not in unique_candidates:
                unique_candidates[key] = c
        candidates = list(unique_candidates.values())

        # Profile enrichment
        if enrich_profiles:
            from .profile_enricher import ProfileEnricher
            profile_enricher = ProfileEnricher()
            candidates = [profile_enricher.enrich_candidate(c) for c in candidates]

        professor_records = [self.normalizer.normalize(candidate) for candidate in candidates]
        publication_records: List[NormalizedPublicationRecord] = []

        should_enrich = enrich_publications if enrich_publications is not None else fixture_path is None
        for professor in professor_records:
            if should_enrich:
                enriched_publications, enrichment_audit = self._enrich_publications_for_professor(professor)
            else:
                enriched_publications = []
                enrichment_audit = [
                    {
                        "source": "publication_enrichment",
                        "matched": False,
                        "reason": "Publication enrichment disabled for fixture-backed run",
                        "confidence": 0.0,
                    }
                ]

            publication_records.extend(enriched_publications)
            professor.publications = [pub.to_dict() for pub in enriched_publications]
            professor.extra.setdefault("publication_enrichment", enrichment_audit)

        duplicates = [candidate.to_dict() for candidate in self.deduper.detect(professor_records)]
        validation_issues = self.validator.validate_professors(professor_records)
        validation_issues.extend(self.validator.validate_publications(publication_records))

        completed_at = datetime.now(timezone.utc).isoformat()
        run_record = ScrapeRunRecord(
            run_id=run_id,
            university=adapter.university,
            department=adapter.department,
            adapter_name=adapter.adapter_name,
            started_at=started_at,
            completed_at=completed_at,
            status="success" if not any(issue.severity == "error" for issue in validation_issues) else "partial",
            pages_attempted=1,
            pages_successful=1,
            records_created=len(professor_records),
            records_updated=0,
            errors_json=[issue.to_dict() for issue in validation_issues if issue.severity == "error"],
            source_urls=[fetch_result.url],
            output_root=str(output_root),
        )
        processed_paths = self.writer.write_processed_outputs(
            fetch_result.source_artifact,
            professor_records,
            publication_records,
            duplicates,
            validation_issues,
            run_record,
        )
        return RunOutputs(
            run_record=run_record,
            raw_path=raw_path,
            processed_paths=processed_paths,
            professor_records=professor_records,
            publication_records=publication_records,
            validation_issues=validation_issues,
            duplicates=duplicates,
        )