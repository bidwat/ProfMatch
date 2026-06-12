from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from sqlmodel import Session

from apps.backend.app.models.scan_job import ScanResult, ScanTask, utcnow
from apps.backend.app.services.agentic_onboarding_service import _call_llm
from apps.backend.app.services.openalex_publication_service import OpenAlexPublicationRevisionService
from apps.backend.app.services.scan_job_service import ScanJobService


class DurableAgenticScanService:
    """Agentic scan pipeline that persists state directly to Postgres.

    No job state is written to JSON. Each extracted professor is saved as a
    scan_result immediately, publications are fetched from OpenAlex and replace
    staged publications, then research summaries are regenerated from bio + the
    OpenAlex publication evidence.
    """

    def __init__(self, session: Session):
        self.session = session
        self.jobs = ScanJobService(session)
        self.openalex = OpenAlexPublicationRevisionService(session)

    async def _crawl_url(self, url: str) -> str:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        from apps.backend.app.services.crawl_policy import crawler_user_agent
        browser_config = BrowserConfig(headless=True, user_agent=crawler_user_agent())
        crawler_config = CrawlerRunConfig(cache_mode=0)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawler_config)
            return result.markdown

    async def run_department_task(self, task: ScanTask) -> dict[str, Any]:
        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "crawl_started", f"Crawling roster page {task.faculty_url}")
        roster_md = await self._crawl_url(task.faculty_url)

        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "extraction_started", "Extracting faculty roster")
        roster_prompt = f"""
        You extract university faculty profiles from a faculty directory page.
        Return STRICT JSON with key "professors" as a list of objects.
        Each object must have:
        - name: full professor name, or null if unavailable
        - profile_url: profile/detail page URL; relative URLs are allowed

        Faculty directory URL: {task.faculty_url}
        University: {task.university}
        Department: {task.department}

        Markdown:
        {roster_md[:50000]}
        """
        roster = _call_llm(roster_prompt, is_json=True)
        profile_links = [p for p in (roster.get("professors") or []) if isinstance(p, dict)]
        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "extraction_completed", f"Found {len(profile_links)} profile candidate(s)")

        saved_results: list[ScanResult] = []
        for idx, prof in enumerate(profile_links):
            name = (prof.get("name") or "").strip()
            profile_url = prof.get("profile_url") or ""
            if not profile_url.startswith("http"):
                profile_url = urljoin(task.faculty_url, profile_url)
            if not name and not profile_url:
                continue
            self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "profile_crawl_started", f"Crawling profile {idx + 1}/{len(profile_links)}: {name or profile_url}")
            try:
                prof_md = await self._crawl_url(profile_url)
                profile_prompt = f"""
                Extract professor profile fields as STRICT JSON:
                - name: full name
                - position: academic title/position
                - email: email address or null
                - homepage: personal/lab homepage URL or null
                - photo: profile photo URL or null
                - bio: research summary or biography text

                Known name: {name}
                Profile URL: {profile_url}
                University: {task.university}
                Department: {task.department}

                Markdown:
                {prof_md[:40000]}
                """
                data = _call_llm(profile_prompt, is_json=True)
                data["name"] = data.get("name") or name
                data["faculty_profile_url"] = profile_url
                data["university"] = task.university
                data["department"] = task.department
                data["publications"] = []
                result = self.jobs.save_scan_results(task.scan_job_id, task.id, [data])
                saved_results.extend(result)
            except Exception as exc:
                self.jobs.append_scan_log(task.scan_job_id, task.id, "warning", "profile_crawl_failed", str(exc), {"profile_url": profile_url, "name": name})

        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "publication_fetch_started", f"Fetching 10 OpenAlex publications for {len(saved_results)} candidate(s)")
        publication_count = 0
        for result in saved_results:
            outcome = self.openalex.fetch_result_publications(result, max_publications=10)
            publication_count += int(outcome.get("publication_count") or 0)

        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "summary_started", "Generating summaries from bio + OpenAlex publications")
        summarized = 0
        for result in saved_results:
            self._summarize_result(result.id)
            summarized += 1

        summary = {
            "professors_found": len(profile_links),
            "candidate_count": len(saved_results),
            "publications_found": publication_count,
            "summaries_generated": summarized,
            "qa_issue_count": sum(len(r.qa_issues or []) for r in saved_results),
        }
        self.jobs.append_scan_log(task.scan_job_id, task.id, "info", "normalization_completed", "Durable scan pipeline completed", summary)
        return summary

    def _summarize_result(self, result_id: int) -> None:
        result = self.session.get(ScanResult, result_id)
        if not result:
            return
        payload = result.professor_payload or {}
        bio = payload.get("bio") or result.research_summary or ""
        publications = result.publications_payload or []
        publication_context = "\n".join(
            f"- {p.get('title')} ({p.get('year')}), {p.get('venue')}: {(p.get('abstract') or '')[:800]}"
            for p in publications[:10]
        )
        prompt = f"""
        Write a concise, source-grounded research summary for an MS/PhD applicant.
        Use only the professor bio/profile text and the publication evidence below.
        Do not invent recruiting status. Mention uncertainty if evidence is thin.

        Professor: {result.professor_name}
        University: {result.university}
        Department: {result.department}
        Title: {result.title or ''}

        Bio/profile text:
        {bio[:4000]}

        Publications:
        {publication_context[:8000]}

        Return 3-5 sentences.
        """
        try:
            summary = _call_llm(prompt, is_json=False)
        except Exception as exc:
            result.qa_issues = [*(result.qa_issues or []), {"severity": "warning", "code": "summary_generation_failed", "message": str(exc)}]
            summary = result.research_summary
        result.research_summary = summary
        payload["durable_summary_generated"] = True
        result.professor_payload = payload
        result.updated_at = utcnow()
        self.session.add(result)
        self.session.commit()
