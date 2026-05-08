from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _convert(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _convert(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _convert(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert(v) for v in value]
    if isinstance(value, tuple):
        return [_convert(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass(slots=True)
class SourceArtifact:
    run_id: str
    university_slug: str
    department_slug: str
    adapter_name: str
    source_type: str
    source_url: str
    artifact_name: str
    fetched_at: str
    status_code: int
    content_type: str
    content_hash: str
    byte_count: int
    encoding: str = "utf-8"
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class FetchResult:
    url: str
    body_text: str
    source_artifact: SourceArtifact
    fetched_at: str
    response_headers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class ProfessorCandidate:
    name: str
    university: str
    department: str
    faculty_profile_url: str
    source_url: str
    source_type: str
    source_confidence: float
    title: Optional[str] = None
    email: Optional[str] = None
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    research_text: Optional[str] = None
    recruiting_signal: str = "unknown"
    recruiting_evidence_url: Optional[str] = None
    recruiting_evidence_text: Optional[str] = None
    openalex_id: Optional[str] = None
    dblp_url: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    google_scholar_url: Optional[str] = None
    extracted_at: str = field(default_factory=utc_now)
    field_sources: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    raw_text: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class PublicationCandidate:
    title: str
    year: int
    venue: str
    url: str
    source: str
    source_author_id: str
    match_confidence: float
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    openalex_id: Optional[str] = None
    dblp_key: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    source_provenance: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    extracted_at: str = field(default_factory=utc_now)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class NormalizedProfessorRecord:
    name: str
    normalized_name: str
    university: str
    department: str
    faculty_profile_url: str
    source_confidence: float
    publications: List[Dict[str, Any]] = field(default_factory=list)
    title: Optional[str] = None
    email: Optional[str] = None
    homepage_url: Optional[str] = None
    research_text: Optional[str] = None
    research_summary: Optional[str] = None
    recruiting_signal: str = "unknown"
    recruiting_evidence_url: Optional[str] = None
    recruiting_evidence_text: Optional[str] = None
    openalex_id: Optional[str] = None
    dblp_url: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    google_scholar_url: Optional[str] = None
    field_sources: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    source_provenance: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class NormalizedPublicationRecord:
    title: str
    year: int
    venue: str
    url: str
    source: str
    source_author_id: str
    match_confidence: float
    abstract: Optional[str] = None
    citation_count: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    openalex_id: Optional[str] = None
    dblp_key: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    source_provenance: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class EnrichmentResult:
    source: str
    matched: bool
    records: List[Dict[str, Any]] = field(default_factory=list)
    reason: Optional[str] = None
    confidence: float = 0.0
    source_author_id: Optional[str] = None
    source_url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    field_name: Optional[str] = None
    record_index: Optional[int] = None
    record_type: Optional[str] = None
    source_url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)


@dataclass(slots=True)
class ScrapeRunRecord:
    run_id: str
    university: str
    department: str
    adapter_name: str
    started_at: str
    completed_at: str
    status: str
    pages_attempted: int
    pages_successful: int
    records_created: int
    records_updated: int
    errors_json: List[Dict[str, Any]] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    output_root: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _convert(self)
