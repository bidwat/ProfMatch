from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseUniversityAdapter
from ..core.run_manager import RunOutputs, ScrapeRunManager
from ..core.models import ScrapeRunRecord


class CMUAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="Carnegie Mellon University",
            department="Computer Science",
            faculty_roster_url="https://csd.cmu.edu/people/faculty",
            adapter_name="cmu",
        )

    def scrape(self, *, run_id: str | None = None, output_root: Path | str = Path("."), fixture_path: Path | None = None, enrich_profiles: bool = True, enrich_publications: bool = False) -> RunOutputs:
        manager = ScrapeRunManager()
        run_id = run_id or manager.generate_run_id()
        output_root = Path(output_root)
        manager.writer.root = output_root

        started_at = datetime.now(timezone.utc).isoformat()
        
        all_candidates = []
        source_urls = []
        pages_attempted = 0
        pages_successful = 0
        
        page = 0
        while True:
            pages_attempted += 1
            url = f"{self.faculty_roster_url}?page={page}"
            try:
                fetch_result = manager.fetcher.fetch(
                    url,
                    run_id=run_id,
                    university=self.university,
                    department=self.department,
                    adapter_name=self.adapter_name,
                    artifact_name=f"roster_p{page}.html",
                    source_type="university_faculty_page",
                )
                manager.writer.write_fetch_result(fetch_result)
                pages_successful += 1
                source_urls.append(url)
                
                candidates = manager.parser.parse_roster_html(
                    fetch_result.body_text,
                    source_url=url,
                    university=self.university,
                    department=self.department,
                )
                
                if not candidates:
                    break
                    
                all_candidates.extend(candidates)
                
                # Check for "Next page" link to decide whether to continue
                if 'rel="next"' not in fetch_result.body_text and "Next page" not in fetch_result.body_text:
                    break
                page += 1
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                break

        unique_candidates = {}
        for c in all_candidates:
            key = c.faculty_profile_url or c.name
            if key not in unique_candidates:
                unique_candidates[key] = c
        all_candidates = list(unique_candidates.values())

        # CMU roster pages include navigation cards; keep only faculty profile links
        filtered_candidates = []
        for c in all_candidates:
            url = (c.faculty_profile_url or "").lower()
            if "/people/faculty/" not in url:
                continue
            cleaned_name = self._clean_candidate_name(c.name)
            slug_name = self._name_from_profile_url(c.faculty_profile_url)
            if not cleaned_name and not slug_name:
                continue
            if cleaned_name and self._looks_like_clean_name(cleaned_name):
                c.name = cleaned_name
            else:
                c.name = slug_name or cleaned_name
            filtered_candidates.append(c)
        all_candidates = filtered_candidates

        if enrich_profiles:
            from ..core.profile_enricher import ProfileEnricher
            enricher = ProfileEnricher()
            all_candidates = [enricher.enrich_candidate(c) for c in all_candidates]

        professor_records = [manager.normalizer.normalize(c) for c in all_candidates]
        duplicates = [c.to_dict() for c in manager.deduper.detect(professor_records)]
        validation_issues = manager.validator.validate_professors(professor_records)
        completed_at = datetime.now(timezone.utc).isoformat()

        run_record = ScrapeRunRecord(
            run_id=run_id,
            university=self.university,
            department=self.department,
            adapter_name=self.adapter_name,
            started_at=started_at,
            completed_at=completed_at,
            status="success" if not any(issue.severity == "error" for issue in validation_issues) else "partial",
            pages_attempted=pages_attempted,
            pages_successful=pages_successful,
            records_created=len(professor_records),
            records_updated=0,
            errors_json=[issue.to_dict() for issue in validation_issues if issue.severity == "error"],
            source_urls=source_urls,
            output_root=str(output_root),
        )

        # Artifact needs to be derived from the first fetch_result or created manually
        # Let's create a dummy source artifact to pass to writer
        from ..core.models import SourceArtifact
        artifact = SourceArtifact(
            run_id=run_id,
            university_slug=self.university_slug,
            department_slug=self.department_slug,
            adapter_name=self.adapter_name,
            source_type="university_faculty_page",
            source_url=self.faculty_roster_url,
            artifact_name="roster.html",
            fetched_at=started_at,
            status_code=200,
            content_type="text/html",
            content_hash="",
            byte_count=0,
            extra={}
        )
        
        processed_paths = manager.writer.write_processed_outputs(
            artifact, professor_records, [], duplicates, validation_issues, run_record
        )
        
        raw_path = manager.writer.raw_dir(artifact)

        return RunOutputs(
            run_record=run_record,
            raw_path=raw_path,
            processed_paths=processed_paths,
            professor_records=professor_records,
            publication_records=[],
            validation_issues=validation_issues,
            duplicates=duplicates,
        )

    def _clean_candidate_name(self, value: str) -> str | None:
        text = " ".join((value or "").split()).strip()
        if not text:
            return None

        # Keep only the front part before contact/location blobs.
        text = re.split(r"\s{2,}|\(\d{3}\)\s*\d{3}|@", text, maxsplit=1)[0].strip()

        # Handle "Last, First ..." entries.
        if "," in text:
            last, rest = text.split(",", 1)
            first_tokens: list[str] = []
            for token in rest.strip().split():
                low = token.lower().strip(".,")
                if low in {
                    "professor",
                    "assistant",
                    "associate",
                    "teaching",
                    "adjunct",
                    "emeritus",
                    "affiliated",
                    "faculty",
                    "research",
                    "program",
                    "director",
                    "design",
                    "systems",
                    "university",
                }:
                    break
                if re.fullmatch(r"[A-Za-z.'-]+", token):
                    first_tokens.append(token)
                else:
                    break
            if first_tokens:
                text = " ".join(first_tokens + [last.strip()])

        # Final safety trim to plausible human name.
        tokens = [t for t in text.split() if re.fullmatch(r"[A-Za-z.'-]+", t)]
        if not (1 <= len(tokens) <= 5):
            return None
        cleaned = " ".join(tokens)
        if cleaned.lower() in {"faculty", "pagination", "directory submenu"}:
            return None
        return cleaned

    def _name_from_profile_url(self, url: str | None) -> str | None:
        if not url:
            return None
        slug = url.rstrip('/').split('/')[-1]
        if not slug or slug in {"faculty", "people"}:
            return None
        parts = [p for p in slug.split('-') if p]
        if not parts:
            return None
        return " ".join(p.capitalize() for p in parts)

    def _looks_like_clean_name(self, name: str) -> bool:
        lowered = name.lower()
        bad = {"university", "design", "systems", "submenu", "pagination"}
        if any(b in lowered for b in bad):
            return False
        return True
