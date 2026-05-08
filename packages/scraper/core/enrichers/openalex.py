from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ..models import EnrichmentResult


class OpenAlexEnricher:
    api_base = "https://api.openalex.org"
    source_name = "openalex"

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
        return {"results": payload}

    def build_author_url(self, author_id: str) -> str:
        author_id = author_id.strip()
        if author_id.startswith("http"):
            return author_id
        return f"{self.api_base}/authors/{author_id}"

    def normalize_author_payload(self, payload: Dict[str, Any], source_author_id: str) -> EnrichmentResult:
        publications: List[Dict[str, Any]] = []
        for work in payload.get("works", []) or payload.get("results", []):
            title = work.get("title") or work.get("display_name")
            if not title:
                continue
            publications.append(
                {
                    "title": title,
                    "year": work.get("publication_year") or work.get("year") or 0,
                    "venue": (work.get("primary_location", {}) or {}).get("source", {}).get("display_name", ""),
                    "url": work.get("doi") or work.get("id") or "",
                    "source": "openalex",
                    "source_author_id": source_author_id,
                    "match_confidence": float(work.get("match_confidence", 1.0)),
                    "abstract": work.get("abstract") or (work.get("abstract_inverted_index") and "[abstract unavailable from inverted index]"),
                    "citation_count": work.get("cited_by_count"),
                    "authors": [a.get("author", {}).get("display_name", "") for a in work.get("authorships", []) if a.get("author")],
                    "openalex_id": work.get("id"),
                    "source_provenance": [{"source": "openalex", "url": self.build_author_url(source_author_id)}],
                }
            )
        return EnrichmentResult(
            source="openalex",
            matched=True,
            records=publications,
            confidence=0.95,
            source_author_id=source_author_id,
            source_url=self.build_author_url(source_author_id),
        )

    def _match_confidence(self, requested_name: str, candidate_name: str) -> float:
        a = " ".join((requested_name or "").lower().split())
        b = " ".join((candidate_name or "").lower().split())
        if not a or not b:
            return 0.0
        if a == b:
            return 0.98
        if a in b or b in a:
            return 0.85
        a_tokens = set(a.split())
        b_tokens = set(b.split())
        overlap = len(a_tokens & b_tokens)
        if overlap >= 2:
            return 0.75
        if overlap == 1:
            return 0.6
        return 0.4

    def enrich_by_author_name(self, author_name: str, *, max_publications: int = 5) -> EnrichmentResult:
        if not author_name.strip():
            return self.skip("Missing author name")

        try:
            search_payload = self._get_json(f"{self.api_base}/authors", params={"search": author_name, "per-page": 1})
        except requests.RequestException as exc:
            return self.skip(f"OpenAlex author search failed: {exc}")

        authors = search_payload.get("results", []) or []
        if not authors:
            return self.skip("OpenAlex author search returned no candidates")

        best_author = authors[0]
        source_author_id = best_author.get("id") or ""
        if not source_author_id:
            return self.skip("OpenAlex candidate missing author id")

        try:
            works_payload = self._get_json(
                f"{self.api_base}/works",
                params={"filter": f"author.id:{source_author_id}", "sort": "publication_year:desc", "per-page": max_publications},
            )
        except requests.RequestException as exc:
            return self.skip(f"OpenAlex works lookup failed: {exc}", source_author_id=source_author_id)

        result = self.normalize_author_payload(works_payload, source_author_id=source_author_id)
        if not result.records:
            return self.skip("OpenAlex returned no publications", source_author_id=source_author_id)

        name_confidence = self._match_confidence(author_name, best_author.get("display_name") or "")
        result.confidence = round(min(result.confidence, name_confidence), 3)
        for record in result.records:
            record["match_confidence"] = round(min(float(record.get("match_confidence", 1.0)), name_confidence), 3)
        return result

    def skip(self, reason: str, source_author_id: Optional[str] = None) -> EnrichmentResult:
        return EnrichmentResult(source="openalex", matched=False, records=[], reason=reason, confidence=0.0, source_author_id=source_author_id)
