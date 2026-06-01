from __future__ import annotations

import os
from typing import Any

import requests
from sqlmodel import Session, select

from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.models.scan_job import ScanResult, utcnow
from apps.backend.app.services.scan_job_service import ScanJobService
from packages.scraper.core.enrichers.openalex import OpenAlexEnricher


class OpenAlexPublicationRevisionService:
    """Bulk publication revision for staged scan candidates.

    Uses OpenAlex institution resolution + institution-filtered author search
    before fetching recent works. This updates scan_results only; it does not
    import into canonical Professor/Publication tables.
    """

    def __init__(self, session: Session):
        self.session = session
        self.job_service = ScanJobService(session)
        self.enricher = OpenAlexEnricher(
            api_key=os.getenv("OPENALEX_API_KEY", "").strip() or None,
            mailto=os.getenv("OPENALEX_MAILTO", "").strip() or None,
        )

    def fetch_job_publications(self, job_id: int, *, max_publications: int = 10, use_llm_verification: bool = False) -> dict[str, Any]:
        results = self.session.exec(select(ScanResult).where(ScanResult.scan_job_id == job_id)).all()
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
        return summary

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
            self.session.add(result)
            self.session.commit()
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
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
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

    def refresh_indexed_department_publications(
        self,
        *,
        university: str,
        department: str,
        max_publications: int = 10,
        max_professors: int = 250,
        regenerate_summaries: bool = True,
    ) -> dict[str, Any]:
        professors = list(
            self.session.exec(
                select(Professor)
                .where(Professor.university == university, Professor.department == department)
                .order_by(Professor.name)
                .limit(max_professors)
            ).all()
        )
        refreshed = 0
        skipped = 0
        errors = 0
        publications_inserted = 0
        for professor in professors:
            try:
                enrichment = self.enricher.enrich_by_author_name_and_institution(
                    professor.name,
                    institution_name=professor.university,
                    max_publications=max_publications,
                )
                if not enrichment.matched or not enrichment.records:
                    skipped += 1
                    continue
                existing = self.session.exec(select(Publication).where(Publication.professor_id == professor.id)).all()
                for publication in existing:
                    self.session.delete(publication)
                for record in enrichment.records[:max_publications]:
                    title = str(record.get("title") or "").strip()
                    if not title:
                        continue
                    self.session.add(Publication(
                        professor_id=professor.id,
                        title=title,
                        year=int(record.get("year") or 0),
                        venue=record.get("venue") or "Unknown",
                        abstract=record.get("abstract"),
                        url=record.get("url"),
                        source="openalex",
                        source_author_id=record.get("source_author_id") or enrichment.source_author_id,
                        match_confidence=float(record.get("match_confidence") or enrichment.confidence or 0.5),
                    ))
                    publications_inserted += 1
                professor.openalex_id = enrichment.source_author_id
                professor.source_confidence = max(float(professor.source_confidence or 0), float(enrichment.confidence or 0))
                professor.updated_at = utcnow()
                if regenerate_summaries:
                    professor.research_summary = self._summary_for_professor(professor, enrichment.records[:max_publications]) or professor.research_summary
                self.session.add(professor)
                refreshed += 1
                self.session.commit()
            except Exception:
                self.session.rollback()
                errors += 1
        return {
            "professors_seen": len(professors),
            "professors_refreshed": refreshed,
            "professors_skipped": skipped,
            "errors": errors,
            "publications_inserted": publications_inserted,
            "max_publications": max_publications,
        }

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
