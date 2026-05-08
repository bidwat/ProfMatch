from __future__ import annotations
import re
from typing import List
from bs4 import BeautifulSoup

from packages.scraper.adapters.base import BaseUniversityAdapter
from packages.scraper.core.models import ProfessorCandidate
from packages.scraper.core.parser import FacultyRosterParser
from packages.scraper.sources.identifiers import canonicalize_url


class TamuCseParser(FacultyRosterParser):
    def parse_roster_html(
        self,
        html: str,
        *,
        source_url: str,
        university: str,
        department: str,
        source_type: str = 'university_faculty_page',
    ) -> List[ProfessorCandidate]:
        candidates: List[ProfessorCandidate] = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all professor profile cards
        cards = soup.select('div.profile')
        
        for card in cards:
            # Extract name
            name_elem = card.select_one('h3.headline-group.profile__headline a span')
            if not name_elem:
                continue
            name = name_elem.text.strip()
            
            # Extract faculty profile URL
            profile_a = card.select_one('h3.headline-group.profile__headline a')
            if not profile_a:
                continue
            profile_href = profile_a.get('href')
            if not profile_href:
                continue
            profile_url = canonicalize_url(profile_href, source_url)
            
            # Extract titles
            title_div = card.select_one('div.profile__titles ul')
            titles = []
            if title_div:
                for li in title_div.find_all('li'):
                    title_text = li.text.strip()
                    if title_text:
                        titles.append(title_text)
            title_str = '; '.join(titles) if titles else None
            
            # Extract email
            email = None
            contact_ul = card.select_one('div.profile__contact ul')
            if contact_ul:
                email_label = contact_ul.find('span', class_='profile__contact-label', string=lambda s: s and 'Email:' in s)
                if email_label:
                    email_li = email_label.find_parent('li')
                    if email_li:
                        email_a = email_li.find('a')
                        if email_a:
                            email = email_a.text.strip()
            
            # Research text and homepage URL not present in roster HTML
            research_text = None
            homepage_url = None
            
            if name and profile_url:
                candidate = ProfessorCandidate(
                    name=name,
                    university=university,
                    department=department,
                    faculty_profile_url=profile_url,
                    source_url=source_url,
                    source_type=source_type,
                    source_confidence=0.9,
                    title=title_str,
                    email=email,
                    research_text=research_text,
                    homepage_url=homepage_url,
                )
                candidates.append(candidate)
        
        return candidates


class TamuCseAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university='Texas A&M University',
            department='Department of Computer Science and Engineering',
            faculty_roster_url='https://engineering.tamu.edu/cse/profiles/index.html#Faculty',
            adapter_name='tamu-cse',
        )
    
    def scrape(self, *, run_id: str | None = None, output_root: str | Path = '.', fixture_path: Path | None = None, enrich_profiles: bool = True, enrich_publications: bool = False):
        from packages.scraper.core.run_manager import ScrapeRunManager
        from pathlib import Path
        manager = ScrapeRunManager(parser=TamuCseParser())
        return manager.run_adapter(
            self,
            run_id=run_id,
            output_root=Path(output_root),
            fixture_path=fixture_path,
            enrich_profiles=enrich_profiles,
            enrich_publications=enrich_publications,
        )