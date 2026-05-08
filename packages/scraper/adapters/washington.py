from __future__ import annotations

from pathlib import Path
from bs4 import BeautifulSoup
from .base import BaseUniversityAdapter
from ..core.run_manager import RunOutputs, ScrapeRunManager
from ..core.models import ScrapeRunRecord, SourceArtifact, ProfessorCandidate
from ..core.profile_enricher import ProfileEnricher
from datetime import datetime, timezone
import time
import asyncio
import re
from crawl4ai import AsyncWebCrawler


class WashingtonAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="University of Washington",
            department="Paul G. Allen School of Computer Science & Engineering",
            faculty_roster_url="https://www.cs.washington.edu/people/faculty-members/",
            adapter_name="uw",
        )

    async def _fetch_and_parse(self, url: str) -> list[tuple[str, str]]:
        """Fetch page with Crawl4AI and parse faculty from profile links."""
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, delay=3)
            html = getattr(result, 'html', '') or ''
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        faculty = []
        seen = set()
        
        # UW: Faculty profiles are at /people/faculty/name-firstname/
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            text = a.get_text(strip=True)
            
            # Must be a faculty profile link
            if '/people/faculty/' not in href:
                continue
            
            # Text should look like a name
            if not re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z\-\.]+)+$', text):
                continue
            
            # Build full URL
            if href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                full_url = f"https://www.cs.washington.edu{href}"
            else:
                continue
            
            if full_url not in seen:
                seen.add(full_url)
                faculty.append((text, full_url))
        
        return faculty

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
        
        pages_attempted += 1
        print(f"Fetching UW Allen School page with Crawl4AI: {self.faculty_roster_url}")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            faculty_links = loop.run_until_complete(self._fetch_and_parse(self.faculty_roster_url))
            loop.close()
            
            if faculty_links:
                pages_successful += 1
                source_urls.append(self.faculty_roster_url)
                print(f"  Found {len(faculty_links)} faculty members")
                
                for name, profile_url in faculty_links:
                    c = ProfessorCandidate(
                        name=name,
                        university=self.university,
                        department=self.department,
                        faculty_profile_url=profile_url,
                        source_url=self.faculty_roster_url,
                        source_type="university_faculty_page",
                        source_confidence=0.9,
                    )
                    all_candidates.append(c)
            else:
                print("  Warning: No faculty links found")
                
        except Exception as e:
            print(f"Error fetching UW page: {e}")

        # Deduplicate
        unique_candidates = {}
        for c in all_candidates:
            key = c.faculty_profile_url or c.name
            if key not in unique_candidates:
                unique_candidates[key] = c
        all_candidates = list(unique_candidates.values())
        
        print(f"Total candidates after dedup: {len(all_candidates)}")
        
        # Enrich profiles
        if enrich_profiles and all_candidates:
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
