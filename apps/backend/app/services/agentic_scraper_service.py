import json
import logging
import os
from pathlib import Path
from typing import Any

from litellm import completion  # type: ignore

from apps.backend.app.db import PROJECT_ROOT

logger = logging.getLogger("profmatch.agentic")


class AgenticScraperService:
    def __init__(self):
        model_name = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash:free").strip()
        if not model_name.startswith("openrouter/"):
            model_name = f"openrouter/{model_name}"
        self.model = model_name

    def generate_adapter(self, url: str) -> dict[str, Any]:
        """
        Takes a URL, fetches the raw HTML using Playwright, and uses an LLM to generate a custom BeautifulSoup adapter.
        """
        html_content = self._fetch_raw_html(url)
        if not html_content:
            raise ValueError(f"Could not fetch HTML from {url}")

        # Basic sanity check to avoid massive payloads if the site is a single-page app or very large
        # We try to trim out <script> and <style> tags to save tokens
        clean_html = self._clean_html(html_content)

        prompt = f"""
You are an expert Python web scraper. You are building a custom adapter for the Professor Match system.

The user has provided a URL for a university faculty directory:
{url}

Here is a snapshot of the raw HTML structure (with scripts and styles removed):
```html
{clean_html[:120000]}  # Trim to avoid exceeding context limits on free models
```

First, determine if this is actually a university faculty or people directory page.
If it is NOT a faculty directory (e.g. a random blog, news article, or error page), set `is_faculty_directory` to false.

If it IS a faculty directory:
1. Extract the `university_name` and `department_name`.
2. Generate an `adapter_slug` (e.g. "ucla", "nyu", "oxford").
3. Write a full Python script containing a custom `BaseUniversityAdapter` and an overridden `FacultyRosterParser`.

Your generated Python code must:
- Import necessary typing, models, and base classes (provided below in the template).
- Include a class `{{TitleSlug}}Parser(FacultyRosterParser)` that overrides `parse_roster_html(...)`. It should use `BeautifulSoup` to find the specific professor cards/rows based on the HTML provided. For each professor, it must extract `name` and `faculty_profile_url` (canonicalized to absolute URLs using `canonicalize_url`). It should also extract `title`, `email`, `research_text`, and `homepage_url` if present.
- Include a class `{{TitleSlug}}Adapter(BaseUniversityAdapter)` that initializes the superclass with the scraped details and overrides the `scrape` method to use your custom parser.

Here is the exact template your Python code MUST follow:
```python
from __future__ import annotations
import re
from typing import List
from bs4 import BeautifulSoup

from packages.scraper.adapters.base import BaseUniversityAdapter
from packages.scraper.core.models import ProfessorCandidate
from packages.scraper.core.parser import FacultyRosterParser
from packages.scraper.sources.identifiers import canonicalize_url

class {{TitleSlug}}Parser(FacultyRosterParser):
    def parse_roster_html(
        self,
        html: str,
        *,
        source_url: str,
        university: str,
        department: str,
        source_type: str = "university_faculty_page",
    ) -> List[ProfessorCandidate]:
        candidates: List[ProfessorCandidate] = []
        soup = BeautifulSoup(html, "html.parser")
        
        # IMPLEMENT YOUR CUSTOM PARSING HERE BASED ON THE HTML STRUCTURE
        # Find all cards/rows representing a professor
        # cards = soup.select("...") 
        
        # for card in cards:
        #     name = ...
        #     profile_url = canonicalize_url(..., source_url)
        #     if name and profile_url:
        #         candidate = ProfessorCandidate(
        #             name=name,
        #             university=university,
        #             department=department,
        #             faculty_profile_url=profile_url,
        #             source_url=source_url,
        #             source_type=source_type,
        #             source_confidence=0.9,
        #             title=...,
        #             email=...,
        #             research_text=...,
        #         )
        #         candidates.append(candidate)

        return candidates

class {{TitleSlug}}Adapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="{{University Name}}",
            department="{{Department Name}}",
            faculty_roster_url="{url}",
            adapter_name="{{adapter_slug}}",
        )

    def scrape(self, *, run_id: str | None = None, output_root: str | Path = ".", fixture_path: Path | None = None, enrich_profiles: bool = True, enrich_publications: bool = False):
        from packages.scraper.core.run_manager import ScrapeRunManager
        from pathlib import Path
        manager = ScrapeRunManager(parser={{TitleSlug}}Parser())
        return manager.run_adapter(
            self,
            run_id=run_id,
            output_root=Path(output_root),
            fixture_path=fixture_path,
            enrich_profiles=enrich_profiles,
            enrich_publications=enrich_publications,
        )
```

Respond STRICTLY with a JSON object in this format (no markdown fences around the JSON):
{{
  "is_faculty_directory": boolean,
  "university_name": "string",
  "department_name": "string",
  "adapter_slug": "string",
  "python_code": "string containing the full python file"
}}
"""

        logger.info(f"Sending HTML snapshot from {url} to {self.model} for analysis...")
        
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            # response_format={"type": "json_object"}  # Removed to support models that don't have native JSON mode
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
            
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to strip markdown fences if the model ignored instructions
            content = content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "", 1)
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content.strip())
            
        if not result.get("is_faculty_directory"):
            return {
                "status": "rejected",
                "message": "The provided URL does not appear to be a university faculty directory."
            }
            
        # Save the adapter
        adapter_slug = result["adapter_slug"].lower().replace("-", "_")
        python_code = result["python_code"]
        
        adapter_path = PROJECT_ROOT / "packages" / "scraper" / "adapters" / f"{adapter_slug}.py"
        adapter_path.write_text(python_code, encoding="utf-8")
        
        # Register the adapter in run_university_scan.py
        self._register_adapter(adapter_slug, result["university_name"], python_code)
        
        return {
            "status": "success",
            "adapter": adapter_slug,
            "university": result["university_name"],
            "department": result["department_name"],
            "message": f"Successfully generated and registered {adapter_slug} adapter."
        }

    def _fetch_raw_html(self, url: str) -> str | None:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Scroll to bottom to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            logger.error(f"Playwright failed to fetch {url}: {e}")
            # Fallback to requests if playwright fails
            import requests
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
                resp.raise_for_status()
                return resp.text
            except Exception as req_e:
                logger.error(f"Requests fallback failed for {url}: {req_e}")
                return None

    def _clean_html(self, html: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "svg", "noscript", "meta", "link", "header", "footer"]):
            tag.decompose()
        return str(soup)

    def _register_adapter(self, adapter_slug: str, university_name: str, python_code: str) -> None:
        # Find the class name in the python code
        import re
        match = re.search(r"class\s+([A-Za-z0-9_]+Adapter)\s*\(BaseUniversityAdapter\)", python_code)
        if not match:
            logger.warning(f"Could not find Adapter class name in generated code for {adapter_slug}")
            return
            
        class_name = match.group(1)
        
        # Add to packages/scraper/adapters/__init__.py
        init_path = PROJECT_ROOT / "packages" / "scraper" / "adapters" / "__init__.py"
        init_content = init_path.read_text(encoding="utf-8")
        
        if f"from .{adapter_slug} import {class_name}" not in init_content:
            init_content = init_content.replace(
                "__all__ = [", 
                f"from .{adapter_slug} import {class_name}\n\n__all__ = [\n    \"{class_name}\","
            )
            init_path.write_text(init_content, encoding="utf-8")
        
        # Add to scripts/project/run_university_scan.py ADAPTERS dictionary
        scan_script_path = PROJECT_ROOT / "scripts" / "project" / "run_university_scan.py"
        scan_content = scan_script_path.read_text(encoding="utf-8")
        
        if f'"{adapter_slug}":' not in scan_content:
            scan_content = re.sub(
                r"(ADAPTERS\s*=\s*\{[^\}]+)(\})",
                rf'\1    "{adapter_slug}": "packages.scraper.adapters.{adapter_slug}:{class_name}",\n\2',
                scan_content
            )
            scan_script_path.write_text(scan_content, encoding="utf-8")
