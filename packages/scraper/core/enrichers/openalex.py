from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ..models import EnrichmentResult


class OpenAlexEnricher:
    api_base = "https://api.openalex.org"
    source_name = "openalex"

    def __init__(self, *, timeout_seconds: int = 20, min_delay_seconds: float = 0.5, user_agent: str = "ProfessorMatchScraper/0.1 (+local MVP)", api_key: Optional[str] = None, mailto: Optional[str] = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.min_delay_seconds = min_delay_seconds
        self.api_key = api_key
        self.mailto = mailto
        self._last_request_at = 0.0
        self.session = requests.Session()
        headers = {"User-Agent": user_agent}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers.update(headers)

    def _pace(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._pace()
        params = dict(params or {})
        if self.mailto and "mailto" not in params:
            params["mailto"] = self.mailto
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

    def resolve_institution_id(self, institution_name: str) -> Optional[str]:
        if not institution_name.strip():
            return None
        try:
            payload = self._get_json(f"{self.api_base}/institutions", params={"search": institution_name, "per-page": 1})
        except requests.RequestException:
            return None
        institutions = payload.get("results", []) or []
        if not institutions:
            return None
        institution_id = institutions[0].get("id") or ""
        return institution_id.rsplit("/", 1)[-1] if institution_id else None

    def _works_for_author(self, source_author_id: str, max_publications: int) -> EnrichmentResult:
        works_payload = self._get_json(
            f"{self.api_base}/works",
            params={"filter": f"authorships.author.id:{source_author_id}", "sort": "publication_year:desc", "per-page": max_publications},
        )
        return self.normalize_author_payload(works_payload, source_author_id=source_author_id)

    def enrich_by_author_name_and_institution(self, author_name: str, *, institution_name: str, max_publications: int = 10) -> EnrichmentResult:
        if not author_name.strip():
            return self.skip("Missing author name")
        institution_id = self.resolve_institution_id(institution_name)
        author_params: Dict[str, Any] = {"search": author_name, "per-page": 5}
        if institution_id:
            author_params["filter"] = f"last_known_institutions.id:{institution_id}"
        try:
            search_payload = self._get_json(f"{self.api_base}/authors", params=author_params)
        except requests.RequestException as exc:
            return self.skip(f"OpenAlex author search failed: {exc}")
        authors = search_payload.get("results", []) or []
        if not authors and institution_id:
            try:
                search_payload = self._get_json(f"{self.api_base}/authors", params={"search": author_name, "per-page": 5})
                authors = search_payload.get("results", []) or []
            except requests.RequestException as exc:
                return self.skip(f"OpenAlex fallback author search failed: {exc}")
        if not authors:
            return self.skip("OpenAlex author search returned no candidates")
        best_author = max(authors, key=lambda a: self._match_confidence(author_name, a.get("display_name") or ""))
        source_author_id = best_author.get("id") or ""
        if not source_author_id:
            return self.skip("OpenAlex candidate missing author id")
        try:
            result = self._works_for_author(source_author_id, max_publications)
        except requests.RequestException as exc:
            return self.skip(f"OpenAlex works lookup failed: {exc}", source_author_id=source_author_id)
        if not result.records:
            return self.skip("OpenAlex returned no publications", source_author_id=source_author_id)
        name_confidence = self._match_confidence(author_name, best_author.get("display_name") or "")
        affiliation_bonus = 0.05 if institution_id and author_params.get("filter") else 0.0
        result.confidence = round(min(0.99, min(result.confidence, name_confidence) + affiliation_bonus), 3)
        for record in result.records:
            record["match_confidence"] = round(min(float(record.get("match_confidence", 1.0)), result.confidence), 3)
            record["openalex_institution_id_used"] = institution_id
        return result

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
