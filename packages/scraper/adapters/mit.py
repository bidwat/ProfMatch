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
import json
from crawl4ai import AsyncWebCrawler


class MITAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="Massachusetts Institute of Technology",
            department="Computer Science and Artificial Intelligence Laboratory",
            faculty_roster_url="https://www.csail.mit.edu/people/?roleFacets=Principal%20Investigators,Core%2FDual,Associates,Emeritus",
            adapter_name="mit",
        )

    def _load_manual_list(self) -> list[tuple[str, str]]:
        """Load faculty list from manual JSON file as fallback."""
        manual_path = Path(__file__).parent.parent.parent.parent / 'data' / 'seeds' / 'mit_csail_faculty.json'
        
        if not manual_path.exists():
            print(f"  Manual list not found at {manual_path}")
            return []
        
        try:
            with open(manual_path) as f:
                data = json.load(f)
            faculty = [(item['name'], item['url']) for item in data]
            print(f"  Loaded {len(faculty)} faculty from manual list")
            return faculty
        except Exception as e:
            print(f"  Error loading manual list: {e}")
            return []

    async def _fetch_and_parse(self, url: str) -> list[tuple[str, str]]:
        """
        Fetch page with Crawl4AI and parse faculty links.
        Note: MIT CSAIL page is heavily JavaScript-dependent.
        Falls back to manual list if page doesn't render properly.
        """
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, wait_for="css:body", js_code="await new Promise(resolve => setTimeout(resolve, 3000));")
            html = getattr(result, 'html', '') or ''
        
        if not html:
            print("  No HTML returned, using manual list")
            return self._load_manual_list()
        
        soup = BeautifulSoup(html, 'html.parser')
        faculty = []
        seen = set()
        
        # MIT CSAIL: Try to find faculty links
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            text = a.get_text(strip=True)
            
            # Skip empty or navigation
            if not text or len(text) < 3 or len(text) > 50:
                continue
            
            # Skip obvious non-faculty
            if any(kw in text.lower() for kw in ['login', 'search', 'menu', 'home', 'news', 'events', 'about', 'contact', 'faculty', 'staff', 'students']):
                continue
            
            # MIT CSAIL profiles are at /people/username
            if '/people/' in href and text and ' ' in text:
                # Text should look like a name
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z\-\.]+)+$', text):
                    full_url = href if href.startswith('http') else f"https://www.csail.mit.edu{href}"
                    if full_url not in seen:
                        seen.add(full_url)
                        faculty.append((text, full_url))
        
        # If we didn't find enough faculty, fall back to manual list
        if len(faculty) < 10:
            print(f"  Warning: Only found {len(faculty)} faculty via Crawl4AI. Using manual list.")
            return self._load_manual_list()
        
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
        
        # Fetch with Crawl4AI
        pages_attempted += 1
        print(f"Fetching MIT CSAIL page with Crawl4AI: {self.faculty_roster_url}")
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
                        source_confidence=0.9 if 'csail.mit.edu' in profile_url else 0.7,
                    )
                    all_candidates.append(c)
            else:
                print("  Warning: No faculty links found. Using manual list.")
                
        except Exception as e:
            print(f"Error fetching MIT page: {e}")
            # Fallback to manual list on error
            faculty_links = self._load_manual_list()
            if faculty_links:
                pages_successful += 1
                source_urls.append("manual_list")
                print(f"  Loaded {len(faculty_links)} faculty from manual list")
                for name, profile_url in faculty_links:
                    c = ProfessorCandidate(
                        name=name,
                        university=self.university,
                        department=self.department,
                        faculty_profile_url=profile_url,
                        source_url="manual_list",
                        source_type="manual_curation",
                        source_confidence=0.8,
                    )
                    all_candidates.append(c)

        # Deduplicate
        unique_candidates = {}
        for c in all_candidates:
            key = c.faculty_profile_url or c.name
            if key not in unique_candidates:
                unique_candidates[key] = c
        all_candidates = list(unique_candidates.values())
        
        print(f"Total candidates after dedup: {len(all_candidates)}")
        
        if not all_candidates:
            print("No faculty found. MIT CSAIL adapter needs improvement or manual data entry.")

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
            status="success" if len(professor_records) > 0 and not any(issue.severity == "error" for issue in validation_issues) else "partial",
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
