import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from litellm import completion  # type: ignore

from apps.backend.app.db import PROJECT_ROOT

logger = logging.getLogger("profmatch.agentic_onboarding")

ONBOARDING_DIR = PROJECT_ROOT / "data" / "qa" / "onboarding"


def _get_model() -> str:
    model_name = os.environ.get("OPENROUTER_MODEL", "inclusionai/ring-2.6-1t:free").strip()
    if not model_name.startswith("openrouter/"):
        model_name = f"openrouter/{model_name}"
    return model_name


def _call_llm(prompt: str, is_json: bool = True) -> Any:
    model = _get_model()
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            # Drop response_format to support models like tencent/hy3-preview:free
        )
        content = response.choices[0].message.content or ""
        
        if is_json:
            try:
                # Clean up markdown fences if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content.replace("```json", "", 1)
                elif content.startswith("```"):
                    content = content.replace("```", "", 1)
                if content.endswith("```"):
                    content = content[:-3]
                
                # Attempt to parse json
                # We can do a bit of recovery if the model returned something weird
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx+1]
                
                return json.loads(content.strip())
            except Exception as json_e:
                logger.error(f"Failed to parse JSON. Raw content: {content}")
                raise json_e
        return content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


class AgenticOnboardingService:
    def __init__(self):
        ONBOARDING_DIR.mkdir(parents=True, exist_ok=True)

    def create_job(self, url: str, university: str, department: str) -> str:
        job_id = str(uuid.uuid4())[:8]
        state = {
            "id": job_id,
            "url": url,
            "university": university,
            "department": department,
            "status": "pending",
            "step": "extract_roster",
            "message": "Initializing...",
            "professors": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._save_state(job_id, state)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = ONBOARDING_DIR / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def stop_job(self, job_id: str) -> bool:
        state = self.get_job(job_id)
        if not state:
            return False
        if state.get("status") in {"running", "pending"}:
            state["stop_requested"] = True
            state["status"] = "stopped"
            state["message"] = "Job stopped by user."
            self._save_state(job_id, state)
            return True
        return False

    def delete_job(self, job_id: str) -> bool:
        path = ONBOARDING_DIR / f"{job_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def _is_stopped(self, job_id: str) -> bool:
        state = self.get_job(job_id)
        return bool(state and state.get("stop_requested"))

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        for path in sorted(ONBOARDING_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                jobs.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return jobs

    def _save_state(self, job_id: str, state: Dict[str, Any]) -> None:
        path = ONBOARDING_DIR / f"{job_id}.json"
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    async def _crawl_url(self, url: str) -> str:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        browser_config = BrowserConfig(headless=True)
        crawler_config = CrawlerRunConfig(cache_mode=0)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawler_config)
            return result.markdown

    async def run_extract_roster(self, job_id: str):
        state = self.get_job(job_id)
        if not state:
            return

        try:
            state["status"] = "running"
            state["message"] = "Crawling roster page..."
            self._save_state(job_id, state)

            roster_md = await self._crawl_url(state["url"])

            state["message"] = "Analyzing roster to find professor profiles..."
            self._save_state(job_id, state)

            prompt = f"""
            You are a helpful AI that extracts university faculty profiles from a webpage.
            I will provide you with the markdown of a faculty directory.
            Find all the professors listed.
            Return a JSON object with a single key "professors" which is a list of objects.
            Each object should have:
            - "name": The full name of the professor.
            - "profile_url": The URL to their specific faculty detail/profile page. If the URL is relative, assume the base URL is {state["url"]}.
            
            Markdown:
            {roster_md[:50000]}
            
            Return STRICTLY valid JSON.
            """
            
            result = _call_llm(prompt, is_json=True)
            profile_links = result.get("professors", [])
            
            professors = []
            for i, prof in enumerate(profile_links):
                if self._is_stopped(job_id):
                    return
                state["message"] = f"Crawling profile {i+1}/{len(profile_links)}: {prof.get('name')}..."
                self._save_state(job_id, state)
                
                profile_url = prof.get("profile_url")
                if not profile_url or not profile_url.startswith("http"):
                    from urllib.parse import urljoin
                    profile_url = urljoin(state["url"], profile_url or "")
                
                try:
                    prof_md = await self._crawl_url(profile_url)
                    
                    extract_prompt = f"""
                    You are extracting specific fields from a professor's profile page.
                    Extract the following into a strict JSON object:
                    - "name": Full name
                    - "position": Academic title/position
                    - "email": Email address (or null)
                    - "homepage": Personal homepage URL (or null)
                    - "photo": Profile photo URL (or null)
                    - "bio": Research summary or biography text
                    
                    Markdown:
                    {prof_md[:40000]}
                    """
                    
                    prof_data = _call_llm(extract_prompt, is_json=True)
                    prof_data["faculty_profile_url"] = profile_url
                    prof_data["publications"] = []
                    prof_data["ai_summary"] = None
                    professors.append(prof_data)
                except Exception as e:
                    logger.error(f"Failed to extract profile {profile_url}: {e}")

            state["professors"] = professors
            state["status"] = "completed"
            state["message"] = f"Successfully extracted {len(professors)} professors."
            self._save_state(job_id, state)

        except Exception as e:
            state["status"] = "error"
            state["message"] = f"Extraction failed: {str(e)}"
            self._save_state(job_id, state)

    async def run_enrich_homepages(self, job_id: str):
        state = self.get_job(job_id)
        if not state or state["status"] != "completed":
            return
            
        try:
            state["status"] = "running"
            state["step"] = "enrich_homepage"
            state["message"] = "Crawling personal homepages..."
            self._save_state(job_id, state)
            
            professors = state.get("professors", [])
            for i, prof in enumerate(professors):
                if self._is_stopped(job_id):
                    return
                homepage = prof.get("homepage")
                if homepage and homepage.startswith("http"):
                    state["message"] = f"Enriching {i+1}/{len(professors)}: {prof.get('name')} from homepage..."
                    self._save_state(job_id, state)
                    
                    try:
                        home_md = await self._crawl_url(homepage)
                        extract_prompt = f"""
                        Extract the research bio/summary from this homepage markdown.
                        If you find additional research interests or bio, return it in a JSON object with the key "additional_bio".
                        
                        Markdown:
                        {home_md[:40000]}
                        """
                        enriched = _call_llm(extract_prompt, is_json=True)
                        add_bio = enriched.get("additional_bio")
                        if add_bio:
                            prof["bio"] = f"{prof.get('bio', '')}\n\nEnriched from Homepage:\n{add_bio}".strip()
                    except Exception as e:
                        logger.error(f"Failed to enrich homepage {homepage}: {e}")
            
            state["professors"] = professors
            state["status"] = "completed"
            state["message"] = "Homepage enrichment complete."
            self._save_state(job_id, state)
            
        except Exception as e:
            state["status"] = "error"
            state["message"] = f"Homepage enrichment failed: {str(e)}"
            self._save_state(job_id, state)

    def run_fetch_publications(self, job_id: str):
        state = self.get_job(job_id)
        if not state or state["status"] != "completed":
            return
            
        try:
            state["status"] = "running"
            state["step"] = "fetch_publications"
            state["message"] = "Fetching publications from DBLP/OpenAlex..."
            self._save_state(job_id, state)
            
            from packages.scraper.core.enrichers import SemanticScholarEnricher, DBLPEnricher
            from packages.scraper.core.models import EnrichmentResult
            
            enrichers = [DBLPEnricher(), SemanticScholarEnricher()]
            
            professors = state.get("professors", [])
            for i, prof in enumerate(professors):
                if self._is_stopped(job_id):
                    return
                state["message"] = f"Fetching papers {i+1}/{len(professors)}: {prof.get('name')}..."
                self._save_state(job_id, state)
                
                pubs = []
                for enricher in enrichers:
                    try:
                        if hasattr(enricher, "enrich_by_author_name"):
                            res: EnrichmentResult = enricher.enrich_by_author_name(prof.get("name"), max_publications=5)
                            for rec in res.records:
                                pubs.append({
                                    "title": rec.get("title"),
                                    "year": rec.get("year"),
                                    "venue": rec.get("venue"),
                                    "url": rec.get("url"),
                                    "abstract": rec.get("abstract")
                                })
                    except Exception as e:
                        logger.error(f"Enricher failed for {prof.get('name')}: {e}")
                        
                prof["publications"] = pubs[:10]  # limit 10
                
            state["professors"] = professors
            state["status"] = "completed"
            state["message"] = "Publication fetching complete."
            self._save_state(job_id, state)
            
        except Exception as e:
            state["status"] = "error"
            state["message"] = f"Publication fetching failed: {str(e)}"
            self._save_state(job_id, state)

    def run_generate_summary(self, job_id: str):
        state = self.get_job(job_id)
        if not state or state["status"] != "completed":
            return
            
        try:
            state["status"] = "running"
            state["step"] = "generate_summary"
            state["message"] = "Generating AI summaries..."
            self._save_state(job_id, state)
            
            professors = state.get("professors", [])
            for i, prof in enumerate(professors):
                if self._is_stopped(job_id):
                    return
                state["message"] = f"Summarizing {i+1}/{len(professors)}: {prof.get('name')}..."
                self._save_state(job_id, state)
                
                pubs_text = "\n".join([f"- {p.get('title')} ({p.get('year')})" for p in prof.get("publications", [])])
                prompt = f"""
                Write a 2-3 sentence AI research summary for this professor.
                
                Name: {prof.get('name')}
                Bio: {prof.get('bio')}
                Recent Publications:
                {pubs_text}
                
                Return a JSON object with a single key "ai_summary" containing the string.
                """
                try:
                    res = _call_llm(prompt, is_json=True)
                    prof["ai_summary"] = res.get("ai_summary")
                except Exception as e:
                    logger.error(f"Summary failed for {prof.get('name')}: {e}")
                    
            state["professors"] = professors
            state["status"] = "completed"
            state["message"] = "AI summary generation complete."
            self._save_state(job_id, state)
            
        except Exception as e:
            state["status"] = "error"
            state["message"] = f"AI summary generation failed: {str(e)}"
            self._save_state(job_id, state)

    def _clean_title(self, title: str | None) -> str | None:
        if not title:
            return None
        import re
        t = re.sub(r'(?i)ORCID.*?(\d{4}-){3}\d{3}[\dX]', '', title)
        t = re.sub(r'(?i)CMU Scholars', '', t)
        return t.strip()

    async def run_automatic_pipeline(self, job_id: str):
        state = self.get_job(job_id)
        if not state:
            return

        try:
            # 1. Extract Roster
            await self.run_extract_roster(job_id)
            if self._is_stopped(job_id): return
            
            # Check if extraction was successful
            state = self.get_job(job_id)
            if state["status"] == "error": return

            # 2. Enrich Homepages
            await self.run_enrich_homepages(job_id)
            if self._is_stopped(job_id): return

            state = self.get_job(job_id)
            if state["status"] == "error": return

            # 3. Fetch Publications
            self.run_fetch_publications(job_id)
            if self._is_stopped(job_id): return

            state = self.get_job(job_id)
            if state["status"] == "error": return

            # 4. Generate AI Summaries
            self.run_generate_summary(job_id)
            if self._is_stopped(job_id): return

            state = self.get_job(job_id)
            if state["status"] == "error": return

            state["status"] = "completed"
            state["step"] = "auto_done"
            state["message"] = "Automatic pipeline complete! Ready to publish."
            self._save_state(job_id, state)

        except Exception as e:
            state = self.get_job(job_id)
            state["status"] = "error"
            state["message"] = f"Automatic pipeline failed: {str(e)}"
            self._save_state(job_id, state)
    def run_publish(self, job_id: str, db):
        state = self.get_job(job_id)
        if not state or state["status"] not in {"completed", "error"}:
            return

        try:
            state["status"] = "running"
            state["step"] = "publish"
            state["message"] = "Publishing to database..."
            self._save_state(job_id, state)

            from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication
            from packages.scraper.sources.identifiers import slugify

            professors_col = db.collection(PROFESSORS)
            publications_col = db.collection(PUBLICATIONS)
            professors = state.get("professors", [])
            inserted_profs = 0
            inserted_pubs = 0

            for prof in professors:
                if self._is_stopped(job_id):
                    return
                # Upsert Professor
                norm_name = slugify(prof.get("name", ""))
                existing = next(
                    (doc for doc in professors_col.find(normalized_name=norm_name) if doc.get("university") == state["university"]),
                    None,
                )
                if not existing:
                    db_prof = Professor(
                        name=prof.get("name"),
                        normalized_name=norm_name,
                        university=state["university"],
                        department=state["department"],
                        faculty_profile_url=prof.get("faculty_profile_url"),
                        title=self._clean_title(prof.get("position")),
                        email=prof.get("email"),
                        homepage_url=prof.get("homepage"),
                        research_text=prof.get("bio"),
                        research_summary=prof.get("ai_summary") or prof.get("bio"),
                        source_confidence=0.9,
                        extra={"image_url": prof.get("photo")} if prof.get("photo") else {}
                    )
                    professor_id = professors_col.add(db_prof.to_doc())
                    inserted_profs += 1
                else:
                    professor_id = existing["id"]
                    patch = {"research_summary": prof.get("ai_summary") or existing.get("research_summary")}
                    if prof.get("photo"):
                        extra = dict(existing.get("extra") or {})
                        extra["image_url"] = prof.get("photo")
                        patch["extra"] = extra
                    professors_col.update(professor_id, patch)

                # Upsert Publications
                for p in prof.get("publications", []):
                    existing_pub = publications_col.find_one(professor_id=professor_id, title=p.get("title"))
                    if not existing_pub:
                        db_pub = Publication(
                            professor_id=professor_id,
                            title=p.get("title"),
                            year=p.get("year") or 0,
                            venue=p.get("venue") or "Unknown",
                            url=p.get("url"),
                            abstract=p.get("abstract"),
                            source="agentic_onboarding",
                            match_confidence=0.9
                        )
                        publications_col.add(db_pub.to_doc())
                        inserted_pubs += 1

            state["status"] = "completed"
            state["message"] = f"Published! Inserted {inserted_profs} professors and {inserted_pubs} publications."
            self._save_state(job_id, state)
            
        except Exception as e:
            import logging
            logging.getLogger("profmatch.agentic").error(f"Publish failed: {e}", exc_info=True)
            state["status"] = "error"
            state["message"] = f"Publish failed: {str(e)}"
            self._save_state(job_id, state)
