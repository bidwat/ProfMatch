"""Professor Match scraper package."""

from .core.models import (
    EnrichmentResult,
    FetchResult,
    NormalizedProfessorRecord,
    NormalizedPublicationRecord,
    ProfessorCandidate,
    PublicationCandidate,
    ScrapeRunRecord,
    SourceArtifact,
    ValidationIssue,
)

__all__ = [
    "EnrichmentResult",
    "FetchResult",
    "NormalizedProfessorRecord",
    "NormalizedPublicationRecord",
    "ProfessorCandidate",
    "PublicationCandidate",
    "ScrapeRunRecord",
    "SourceArtifact",
    "ValidationIssue",
]
