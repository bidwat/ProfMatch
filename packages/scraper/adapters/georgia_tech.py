from __future__ import annotations

from pathlib import Path
from .base import BaseUniversityAdapter
from ..core.run_manager import RunOutputs, ScrapeRunManager
from ..core.models import ScrapeRunRecord, SourceArtifact
from ..core import parser as parser_module
from ..core.profile_enricher import ProfileEnricher
from datetime import datetime, timezone
import time


class GeorgiaTechAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="Georgia Institute of Technology",
            department="Computer Science",
            faculty_roster_url="https://www.cc.gatech.edu/people/faculty",
            adapter_name="gatech",
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
        
        # Georgia Tech might have pagination or all on one page
        # Let's check the main page first
        page = 0
        while True:
            pages_attempted += 1
            url = self.faculty_roster_url
            if page > 0:
                # Try common pagination patterns
                if '?' in url:
                    url = f"{url}&page={page}"
                else:
                    url = f"{url}?page={page}"
            
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
                print(f"  Page {page}: Found {len(candidates)} candidates")
                
                # Check for next page link or if we got fewer candidates than expected
                if 'rel="next"' not in fetch_result.body_text and "Next" not in fetch_result.body_text:
                    if page > 0:
                        break
                
                page += 1
                if page > 10:  # safety limit
                    break
                
                time.sleep(1)  # be nice
                
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                break

        # Deduplicate
        unique_candidates = {}
        for c in all_candidates:
            key = c.faculty_profile_url or c.name
            if key not in unique_candidates:
                unique_candidates[key] = c
        all_candidates = list(unique_candidates.values())

        print(f"Total candidates after dedup: {len(all_candidates)}")

        # Enrich profiles
        if enrich_profiles:
            print(f"Enriching {len(all_candidates)} candidates...")
            enricher = ProfileEnricher()
            enriched = []
            for c in all_candidates:
                try:
                    enriched_c = enricher.enrich_candidate(c)
                    enriched.append(enriched_c)
                except Exception as e:
                    print(f"Error enriching {c.name}: {e}")
                    enriched.append(c)
                time.sleep(1)
            all_candidates = enriched

        # Normalize
        professor_records = [manager.normalizer.normalize(c) for c in all_candidates]
        
        # Detect duplicates and validate
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
