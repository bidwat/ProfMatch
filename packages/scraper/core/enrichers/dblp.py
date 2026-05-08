from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import requests

from ..models import EnrichmentResult


class DBLPEnricher:
    source_name = "dblp"

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

    def build_author_url(self, dblp_key_or_url: str) -> str:
        if dblp_key_or_url.startswith("http"):
            return dblp_key_or_url
        return f"https://dblp.org/pid/{dblp_key_or_url}.html"

    def _extract_pid(self, author_url: str) -> Optional[str]:
        match = re.search(r"/pid/(.+?)\.html", author_url or "")
        if match:
            return match.group(1)
        return None

    def _coerce_r_list(self, r_value: Any) -> List[Dict[str, Any]]:
        if isinstance(r_value, list):
            return [entry for entry in r_value if isinstance(entry, dict)]
        if isinstance(r_value, dict):
            return [r_value]
        return []

    def _extract_authors(self, author_blob: Any) -> List[str]:
        if not author_blob:
            return []
        if isinstance(author_blob, str):
            return [author_blob]
        if isinstance(author_blob, list):
            names: List[str] = []
            for entry in author_blob:
                if isinstance(entry, str):
                    names.append(entry)
                elif isinstance(entry, dict):
                    names.append(entry.get("text") or entry.get("#text") or "")
            return [name for name in names if name]
        if isinstance(author_blob, dict):
            if "text" in author_blob:
                return [author_blob["text"]]
            if "#text" in author_blob:
                return [author_blob["#text"]]
        return []

    def normalize_publications(self, publications: List[Dict[str, Any]], source_author_id: str) -> EnrichmentResult:
        records = []
        for pub in publications:
            title = pub.get("title")
            if not title:
                continue
            records.append(
                {
                    "title": title,
                    "year": int(pub.get("year") or 0),
                    "venue": pub.get("venue") or "",
                    "url": pub.get("url") or pub.get("ee") or "",
                    "source": "dblp",
                    "source_author_id": source_author_id,
                    "match_confidence": float(pub.get("match_confidence", 1.0)),
                    "authors": pub.get("authors") or [],
                    "dblp_key": pub.get("dblp_key"),
                    "source_provenance": [{"source": "dblp", "url": self.build_author_url(source_author_id)}],
                }
            )
        return EnrichmentResult(
            source="dblp",
            matched=bool(records),
            records=records,
            confidence=0.9 if records else 0.0,
            source_author_id=source_author_id,
            source_url=self.build_author_url(source_author_id),
            reason=None if records else "No DBLP publications found",
        )

    def _publications_from_author_payload(self, payload: Dict[str, Any], *, max_publications: int) -> List[Dict[str, Any]]:
        person = payload.get("dblpperson", {}) or {}
        entries = self._coerce_r_list(person.get("r"))
        records: List[Dict[str, Any]] = []
        for wrapper in entries:
            if len(records) >= max_publications:
                break
            if not wrapper:
                continue
            _, value = next(iter(wrapper.items()))
            if not isinstance(value, dict):
                continue
            info = value.get("info", {}) or {}
            title = info.get("title")
            if not title:
                continue
            records.append(
                {
                    "title": title,
                    "year": info.get("year") or 0,
                    "venue": info.get("venue") or info.get("booktitle") or info.get("journal") or "",
                    "url": info.get("ee") or info.get("url") or "",
                    "authors": self._extract_authors(info.get("authors", {}).get("author") if isinstance(info.get("authors"), dict) else info.get("authors")),
                    "dblp_key": info.get("key"),
                }
            )
        return records

    def enrich_by_author_name(self, author_name: str, *, max_publications: int = 5) -> EnrichmentResult:
        if not author_name.strip():
            return self.skip("Missing author name")

        try:
            search_payload = self._get_json(
                "https://dblp.org/search/author/api",
                params={"q": author_name, "format": "json", "h": 1},
            )
        except requests.RequestException as exc:
            return self.skip(f"DBLP author search failed: {exc}")

        hits = (((search_payload.get("result") or {}).get("hits") or {}).get("hit") or [])
        if isinstance(hits, dict):
            hits = [hits]
        if not hits:
            return self.skip("DBLP author search returned no candidates")

        best = hits[0].get("info", {})
        author_url = best.get("url") or ""
        pid = self._extract_pid(author_url)
        if not pid:
            return self.skip("DBLP author candidate missing pid")

        try:
            author_payload = self._get_json(f"https://dblp.org/pid/{pid}.json")
        except requests.RequestException as exc:
            return self.skip(f"DBLP author publications lookup failed: {exc}", source_author_id=pid)

        publications = self._publications_from_author_payload(author_payload, max_publications=max_publications)
        result = self.normalize_publications(publications, source_author_id=pid)
        if not result.records:
            return self.skip("DBLP returned no publications", source_author_id=pid)
        return result

    def skip(self, reason: str, source_author_id: Optional[str] = None) -> EnrichmentResult:
        return EnrichmentResult(source="dblp", matched=False, records=[], reason=reason, confidence=0.0, source_author_id=source_author_id)
