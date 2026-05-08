from __future__ import annotations

from collections import Counter
from typing import Dict, Sequence

from .models import NormalizedProfessorRecord, NormalizedPublicationRecord, ValidationIssue
from .types import RecruitingSignal


class RecordValidator:
    professor_required_fields = ["name", "university", "department", "faculty_profile_url", "source_confidence"]
    publication_required_fields = ["title", "year", "venue", "url", "source", "source_author_id", "match_confidence"]

    def validate_professors(self, records: Sequence[NormalizedProfessorRecord]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for idx, record in enumerate(records):
            for field in self.professor_required_fields:
                value = getattr(record, field)
                if value in (None, ""):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="missing_required_field",
                            message=f"Missing required professor field: {field}",
                            field_name=field,
                            record_index=idx,
                            record_type="professor",
                        )
                    )
            if not isinstance(record.source_confidence, (int, float)) or not (0.0 <= float(record.source_confidence) <= 1.0):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_source_confidence",
                        message="source_confidence must be numeric between 0 and 1",
                        field_name="source_confidence",
                        record_index=idx,
                        record_type="professor",
                    )
                )
            if record.recruiting_signal not in {signal.value for signal in RecruitingSignal}:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_recruiting_signal",
                        message="recruiting_signal must be positive, negative, or unknown",
                        field_name="recruiting_signal",
                        record_index=idx,
                        record_type="professor",
                    )
                )
            if record.recruiting_signal in {RecruitingSignal.POSITIVE.value, RecruitingSignal.NEGATIVE.value}:
                if not record.recruiting_evidence_url or not record.recruiting_evidence_text:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="missing_recruiting_evidence",
                            message="Positive/negative recruiting signal requires evidence URL and text",
                            field_name="recruiting_signal",
                            record_index=idx,
                            record_type="professor",
                        )
                    )
            if record.research_text and not record.field_sources.get("research_text"):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="missing_research_provenance",
                        message="research_text exists but field_sources.research_text is missing",
                        field_name="research_text",
                        record_index=idx,
                        record_type="professor",
                    )
                )
        return issues

    def validate_publications(self, records: Sequence[NormalizedPublicationRecord]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for idx, record in enumerate(records):
            for field in self.publication_required_fields:
                value = getattr(record, field)
                if value in (None, ""):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="missing_required_field",
                            message=f"Missing required publication field: {field}",
                            field_name=field,
                            record_index=idx,
                            record_type="publication",
                        )
                    )
        return issues

    def confidence_distribution(self, records: Sequence[NormalizedProfessorRecord]) -> Dict[str, int]:
        counts = Counter()
        for record in records:
            score = float(record.source_confidence or 0)
            if score >= 0.85:
                counts["high"] += 1
            elif score >= 0.7:
                counts["medium"] += 1
            elif score >= 0.4:
                counts["low"] += 1
            else:
                counts["very_low"] += 1
        return dict(counts)
