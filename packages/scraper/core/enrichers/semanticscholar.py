from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ..models import EnrichmentResult


class SemanticScholarEnricher:
    api_base = "https://api.semanticscholar.org/graph/v1"
    source_name = "semantic_scholar"

    def __init__(self, *, timeout_seconds: int = 20, min_delay_seconds: float = 0.5, user_agent: str = "ProfessorMatchScraper/0.1 (+local MVP)") -> None:
        self.timeout_seconds = timeout_seconds
        self.min_delay_seconds = min_delay_seconds
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _pace(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._pace()
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {}

    def build_paper_url(self, paper_id: str) -> str:
        if paper_id.startswith("http"):
            return paper_id
        return f"{self.api_base}/paper/{paper_id}"

    def normalize_paper(self, payload: Dict[str, Any], source_author_id: str) -> EnrichmentResult:
        record = {
            "title": payload.get("title") or payload.get("paperTitle") or "",
            "year": payload.get("year") or payload.get("publicationYear") or 0,
            "venue": payload.get("venue") or payload.get("journal") or "",
            "url": payload.get("url") or payload.get("externalIds", {}).get("DOI", ""),
            "source": "semantic_scholar",
            "source_author_id": source_author_id,
            "match_confidence": float(payload.get("match_confidence", 1.0)),
            "abstract": payload.get("abstract"),
            "citation_count": payload.get("citationCount"),
            "authors": [author.get("name", "") for author in payload.get("authors", []) if author.get("name")],
            "semantic_scholar_id": payload.get("paperId") or payload.get("paper_id"),
            "source_provenance": [{"source": "semantic_scholar", "url": self.build_paper_url(payload.get("paperId") or payload.get("paper_id") or source_author_id)}],
        }
        matched = bool(record["title"])
        return EnrichmentResult(
            source="semantic_scholar",
            matched=matched,
            records=[record] if matched else [],
            confidence=0.9 if matched else 0.0,
            source_author_id=source_author_id,
            source_url=self.build_paper_url(payload.get("paperId") or payload.get("paper_id") or source_author_id),
            reason=None if matched else "Missing paper title",
        )

    def enrich_by_author_name(self, author_name: str, *, max_publications: int = 5) -> EnrichmentResult:
        if not author_name.strip():
            return self.skip("Missing author name")

        try:
            search_payload = self._get_json(
                f"{self.api_base}/author/search",
                params={"query": author_name, "limit": 1, "fields": "name,paperCount"},
            )
        except requests.RequestException as exc:
            return self.skip(f"Semantic Scholar author search failed: {exc}")

        candidates = search_payload.get("data") or []
        if not candidates:
            return self.skip("Semantic Scholar author search returned no candidates")

        best_author = candidates[0]
        author_id = best_author.get("authorId") or best_author.get("author_id")
        if not author_id:
            return self.skip("Semantic Scholar author candidate missing authorId")

        try:
            papers_payload = self._get_json(
                f"{self.api_base}/author/{author_id}/papers",
                params={"limit": max_publications, "fields": "title,year,venue,abstract,url,citationCount,authors,externalIds,paperId"},
            )
        except requests.RequestException as exc:
            return self.skip(f"Semantic Scholar papers lookup failed: {exc}", source_author_id=str(author_id))

        papers: List[Dict[str, Any]] = papers_payload.get("data") or []
        records: List[Dict[str, Any]] = []
        for paper in papers:
            paper_result = self.normalize_paper(paper, source_author_id=str(author_id))
            if paper_result.records:
                records.extend(paper_result.records)

        if not records:
            return self.skip("Semantic Scholar returned no publications", source_author_id=str(author_id))

        return EnrichmentResult(
            source="semantic_scholar",
            matched=True,
            records=records,
            confidence=0.9,
            source_author_id=str(author_id),
            source_url=f"{self.api_base}/author/{author_id}",
        )

    def skip(self, reason: str, source_author_id: Optional[str] = None) -> EnrichmentResult:
        return EnrichmentResult(source="semantic_scholar", matched=False, records=[], reason=reason, confidence=0.0, source_author_id=source_author_id)
