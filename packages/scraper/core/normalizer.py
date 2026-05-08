from __future__ import annotations

from datetime import datetime, timezone

from .models import NormalizedProfessorRecord, NormalizedPublicationRecord, ProfessorCandidate, PublicationCandidate
from ..sources.identifiers import normalize_name


class ProfessorNormalizer:
    def normalize(self, candidate: ProfessorCandidate) -> NormalizedProfessorRecord:
        now = datetime.now(timezone.utc).isoformat()
        research_summary = None
        if candidate.research_text:
            research_summary = candidate.research_text.strip()
            if len(research_summary) > 220:
                research_summary = research_summary[:217].rsplit(" ", 1)[0] + "..."

        field_sources = dict(candidate.field_sources)
        field_sources.setdefault(
            "source_confidence",
            [{"source_type": candidate.source_type, "url": candidate.source_url, "confidence": candidate.source_confidence}],
        )
        source_provenance = [{"field": field, "sources": sources} for field, sources in field_sources.items()]

        return NormalizedProfessorRecord(
            name=candidate.name,
            normalized_name=normalize_name(candidate.name),
            university=candidate.university,
            department=candidate.department,
            faculty_profile_url=candidate.faculty_profile_url,
            source_confidence=max(0.0, min(1.0, candidate.source_confidence)),
            title=candidate.title,
            email=candidate.email,
            homepage_url=candidate.homepage_url,
            research_text=candidate.research_text,
            research_summary=research_summary,
            recruiting_signal=candidate.recruiting_signal or "unknown",
            recruiting_evidence_url=candidate.recruiting_evidence_url,
            recruiting_evidence_text=candidate.recruiting_evidence_text,
            openalex_id=candidate.openalex_id,
            dblp_url=candidate.dblp_url,
            semantic_scholar_id=candidate.semantic_scholar_id,
            google_scholar_url=candidate.google_scholar_url,
            field_sources=field_sources,
            source_provenance=source_provenance,
            created_at=now,
            updated_at=now,
            extra=dict(candidate.extra),
        )


class PublicationNormalizer:
    def normalize(self, candidate: PublicationCandidate) -> NormalizedPublicationRecord:
        return NormalizedPublicationRecord(
            title=candidate.title,
            year=int(candidate.year),
            venue=candidate.venue,
            url=candidate.url,
            source=candidate.source,
            source_author_id=candidate.source_author_id,
            match_confidence=max(0.0, min(1.0, candidate.match_confidence)),
            abstract=candidate.abstract,
            citation_count=candidate.citation_count,
            authors=list(candidate.authors),
            openalex_id=candidate.openalex_id,
            dblp_key=candidate.dblp_key,
            semantic_scholar_id=candidate.semantic_scholar_id,
            source_provenance=[{"source": candidate.source, "url": candidate.url}],
            extra=dict(candidate.extra),
        )
