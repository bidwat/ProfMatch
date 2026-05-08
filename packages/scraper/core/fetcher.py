from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

from .models import FetchResult, SourceArtifact, utc_now
from ..sources.catalog import allowed_domain
from ..sources.identifiers import canonicalize_url, hash_text, slugify


class SafeFetcher:
    def __init__(
        self,
        *,
        user_agent: str = "ProfessorMatchScraper/0.1 (+local MVP)",
        timeout_seconds: int = 20,
        min_delay_seconds: float = 1.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.min_delay_seconds = min_delay_seconds
        self._last_fetch_at = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _respect_pacing(self) -> None:
        elapsed = time.monotonic() - self._last_fetch_at
        remaining = self.min_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_fetch_at = time.monotonic()

    def fetch(
        self,
        url: str,
        *,
        run_id: str,
        university: str,
        department: str,
        adapter_name: str,
        artifact_name: str = "roster.html",
        source_type: str = "university_faculty_page",
        allowed_domains_only: bool = False,
        extra: Optional[Dict[str, object]] = None,
    ) -> FetchResult:
        url = canonicalize_url(url)
        if allowed_domains_only and urlparse(url).scheme in {"http", "https"} and not allowed_domain(url):
            raise ValueError(f"Disallowed source domain for URL: {url}")

        self._respect_pacing()
        fetched_at = utc_now()
        status_code = 200
        headers: Dict[str, object] = {}

        if url.startswith("file://"):
            path = Path(urlparse(url).path)
            body_text = path.read_text(encoding="utf-8")
            content_type = "text/html; charset=utf-8"
        elif urlparse(url).scheme in {"", "path"}:
            path = Path(url)
            body_text = path.read_text(encoding="utf-8")
            content_type = "text/html; charset=utf-8"
        else:
            response = self.session.get(url, timeout=self.timeout_seconds)
            status_code = response.status_code
            response.raise_for_status()
            body_text = response.text
            content_type = response.headers.get("content-type", "text/html")
            headers = dict(response.headers)

        content_hash = hash_text(body_text)
        artifact = SourceArtifact(
            run_id=run_id,
            university_slug=slugify(university),
            department_slug=slugify(department),
            adapter_name=adapter_name,
            source_type=source_type,
            source_url=url,
            artifact_name=artifact_name,
            fetched_at=fetched_at,
            status_code=status_code,
            content_type=content_type,
            content_hash=content_hash,
            byte_count=len(body_text.encode("utf-8")),
            extra=extra or {},
        )
        return FetchResult(url=url, body_text=body_text, source_artifact=artifact, fetched_at=fetched_at, response_headers=headers)
