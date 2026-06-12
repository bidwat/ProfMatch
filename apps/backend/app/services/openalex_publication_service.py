from __future__ import annotations

import os
from typing import Any

from apps.backend.app.db import Database
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication
from apps.backend.app.models.scan_job import ScanResult, utcnow
from apps.backend.app.services.scan_job_service import ScanJobService
from packages.scraper.core.enrichers.openalex import OpenAlexEnricher


class OpenAlexPublicationRevisionService:
    """Bulk publication revision for staged scan candidates.

    Uses OpenAlex institution resolution + institution-filtered author search
    before fetching recent works. This updates scan_results only; it does not
    import into the canonical professors/publications collections.
    """

    def __init__(self, db: Database):
        self.db = db
        self.job_service = ScanJobService(db)
        self.professors = db.collection(PROFESSORS)
        self.publications = db.collection(PUBLICATIONS)
        self.enricher = OpenAlexEnricher(
            api_key=os.getenv("OPENALEX_API_KEY", "").strip() or None,
            mailto=os.getenv("OPENALEX_MAILTO", "").strip() or None,
        )

    def fetch_job_publications(self, job_id: int, *, max_publications: int = 10, use_llm_verification: bool = False) -> dict[str, Any]:
        results = self.job_service.list_scan_results(job_id, limit=1000)
        self.job_service.append_scan_log(
            job_id,
            None,
            "info",
            "publication_fetch_started",
            f"Fetching replacement publications with OpenAlex for {len(results)} candidate(s)",
            {"max_publications": max_publications, "use_llm_verification": use_llm_verification},
        )
        revised = 0
        skipped = 0
        errors = 0
        total_publications = 0
        for result in results:
            try:
                outcome = self.fetch_result_publications(result, max_publications=max_publications)
                if outcome["revised"]:
                    revised += 1
                    total_publications += outcome["publication_count"]
                else:
                    skipped += 1
            except Exception as exc:
                errors += 1
                self.job_service.append_scan_log(job_id, result.scan_task_id, "error", "publication_revision_failed", str(exc), {"result_id": result.id})
        summary = {"revised_results": revised, "skipped_results": skipped, "errors": errors, "publication_count": total_publications}
        self.job_service.append_scan_log(job_id, None, "info", "publication_fetch_completed", "OpenAlex publication fetch completed", summary)
        return summary

    def revise_job_publications(self, job_id: int, *, max_publications: int = 10, use_llm_verification: bool = False) -> dict[str, Any]:
        return self.fetch_job_publications(job_id, max_publications=max_publications, use_llm_verification=use_llm_verification)

    def fetch_result_publications(self, result: ScanResult, *, max_publications: int = 10) -> dict[str, Any]:
        if not result.professor_name.strip():
            return {"revised": False, "publication_count": 0, "reason": "missing professor name"}
        enrichment = self.enricher.enrich_by_author_name_and_institution(
            result.professor_name,
            institution_name=result.university,
            max_publications=max_publications,
        )
        if not enrichment.matched or not enrichment.records:
            result.publications_payload = []
            result.qa_issues = [*(result.qa_issues or []), {"severity": "warning", "code": "openalex_no_match", "message": enrichment.reason or "OpenAlex returned no verified publications"}]
            result.updated_at = utcnow()
            self.job_service.save_scan_result(result)
            return {"revised": False, "publication_count": 0, "reason": enrichment.reason}

        # Replace old staged publications with the OpenAlex-backed set.
        result.publications_payload = enrichment.records[:max_publications]
        result.source_confidence = max(float(result.source_confidence or 0), float(enrichment.confidence or 0))
        payload = dict(result.professor_payload or {})
        payload["openalex_author_id"] = enrichment.source_author_id
        payload["openalex_source_url"] = enrichment.source_url
        payload["openalex_publication_revision"] = {
            "matched": enrichment.matched,
            "confidence": enrichment.confidence,
            "publication_count": len(result.publications_payload),
        }
        result.professor_payload = payload
        result.updated_at = utcnow()
        self.job_service.save_scan_result(result)
        self.job_service.append_scan_log(
            result.scan_job_id,
            result.scan_task_id,
            "info",
            "publication_fetch_result_saved",
            f"Replaced staged publications with {len(result.publications_payload)} OpenAlex publication(s) for {result.professor_name}",
            {"result_id": result.id, "author_id": enrichment.source_author_id, "confidence": enrichment.confidence},
        )
        return {"revised": True, "publication_count": len(result.publications_payload)}

    def revise_result_publications(self, result: ScanResult, *, max_publications: int = 10) -> dict[str, Any]:
        return self.fetch_result_publications(result, max_publications=max_publications)

    def _department_professors(self, university: str, department: str, max_professors: int) -> list[Professor]:
        professors = [
            Professor.from_doc(doc)
            for doc in self.professors.all()
            if doc.get("university") == university and doc.get("department") == department
        ]
        professors.sort(key=lambda p: p.name or "")
        return professors[:max_professors]

    def refresh_indexed_department_publications(
        self,
        *,
        university: str,
        department: str,
        max_publications: int = 10,
        max_professors: int = 250,
        regenerate_summaries: bool = False,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        professors = self._department_professors(university, department, max_professors)
        refreshed = 0
        skipped = 0
        errors = 0
        publications_inserted = 0
        for index, professor in enumerate(professors, start=1):
            if progress_callback:
                progress_callback(index - 1, len(professors), f"Fetching OpenAlex publications for {professor.name}")
            try:
                enrichment = self.enricher.enrich_by_author_name_and_institution(
                    professor.name,
                    institution_name=professor.university,
                    max_publications=max_publications,
                )
                if not enrichment.matched or not enrichment.records:
                    skipped += 1
                    continue
                for publication in self.publications.find(professor_id=professor.id):
                    self.publications.delete(publication["id"])
                for record in enrichment.records[:max_publications]:
                    title = str(record.get("title") or "").strip()
                    if not title:
                        continue
                    self.publications.add(Publication(
                        professor_id=professor.id,
                        title=title,
                        year=int(record.get("year") or 0),
                        venue=record.get("venue") or "Unknown",
                        abstract=record.get("abstract"),
                        url=record.get("url"),
                        source="openalex",
                        source_author_id=record.get("source_author_id") or enrichment.source_author_id,
                        match_confidence=float(record.get("match_confidence") or enrichment.confidence or 0.5),
                    ).to_doc())
                    publications_inserted += 1
                patch: dict[str, Any] = {
                    "openalex_id": enrichment.source_author_id,
                    "source_confidence": max(float(professor.source_confidence or 0), float(enrichment.confidence or 0)),
                    "updated_at": utcnow(),
                }
                if regenerate_summaries:
                    summary = self._summary_for_professor(professor, enrichment.records[:max_publications])
                    if summary:
                        patch["research_summary"] = summary
                self.professors.update(professor.id, patch)
                refreshed += 1
            except Exception:
                errors += 1
        if progress_callback:
            progress_callback(len(professors), len(professors), "OpenAlex publication refresh complete")
        return {
            "professors_seen": len(professors),
            "professors_refreshed": refreshed,
            "professors_skipped": skipped,
            "errors": errors,
            "publications_inserted": publications_inserted,
            "max_publications": max_publications,
            "summaries_regenerated": regenerate_summaries,
        }

    def enrich_indexed_department_profiles(
        self,
        *,
        university: str,
        department: str,
        max_professors: int = 250,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        professors = self._department_professors(university, department, max_professors)
        enriched = 0
        skipped = 0
        errors = 0
        for index, professor in enumerate(professors, start=1):
            if progress_callback:
                progress_callback(index - 1, len(professors), f"Enriching profile for {professor.name}")
            try:
                publications = [
                    {
                        "title": publication.get("title"),
                        "year": publication.get("year"),
                        "venue": publication.get("venue"),
                        "abstract": publication.get("abstract"),
                    }
                    for publication in self.publications.find(professor_id=professor.id)
                ]
                if not (professor.research_text or professor.research_summary or publications):
                    skipped += 1
                    continue
                summary = self._summary_for_professor(professor, publications)
                if not summary:
                    skipped += 1
                    continue
                self.professors.update(professor.id, {"research_summary": summary, "updated_at": utcnow()})
                enriched += 1
            except Exception:
                errors += 1
        if progress_callback:
            progress_callback(len(professors), len(professors), "Profile enrichment complete")
        return {"professors_seen": len(professors), "professors_enriched": enriched, "professors_skipped": skipped, "errors": errors}

    def _summary_for_professor(self, professor: Professor, publications: list[dict[str, Any]]) -> str | None:
        if not publications:
            return None
        from apps.backend.app.services.agentic_onboarding_service import _call_llm
        publication_context = "\n".join(
            f"- {p.get('title')} ({p.get('year')}), {p.get('venue')}: {(p.get('abstract') or '')[:700]}"
            for p in publications[:10]
        )
        prompt = f"""
        Write a concise professor research summary using only the profile text and publication evidence below.
        Do not invent recruiting status.

        Professor: {professor.name}
        University: {professor.university}
        Department: {professor.department}
        Existing profile/research text:
        {(professor.research_text or professor.research_summary or '')[:4000]}

        OpenAlex publications:
        {publication_context[:8000]}

        Return 3-5 sentences.
        """
        try:
            return str(_call_llm(prompt, is_json=False)).strip()
        except Exception:
            return None
