from __future__ import annotations

import unittest

from packages.scraper.core.models import NormalizedProfessorRecord, NormalizedPublicationRecord
from packages.scraper.core.validator import RecordValidator


class ValidatorTests(unittest.TestCase):
    def test_valid_professor_record_passes(self) -> None:
        record = NormalizedProfessorRecord(
            name="Jane Doe",
            normalized_name="doe jane",
            university="Stanford University",
            department="Computer Science",
            faculty_profile_url="https://example.edu/jane",
            source_confidence=0.92,
            field_sources={"name": [{"source_type": "university_faculty_page", "url": "https://example.edu/faculty", "confidence": 0.92}]},
        )
        issues = RecordValidator().validate_professors([record])
        self.assertEqual([], issues)

    def test_positive_recruiting_requires_evidence(self) -> None:
        record = NormalizedProfessorRecord(
            name="Jane Doe",
            normalized_name="doe jane",
            university="Stanford University",
            department="Computer Science",
            faculty_profile_url="https://example.edu/jane",
            source_confidence=0.92,
            recruiting_signal="positive",
        )
        issues = RecordValidator().validate_professors([record])
        self.assertTrue(any(issue.code == "missing_recruiting_evidence" for issue in issues))

    def test_publication_required_fields(self) -> None:
        record = NormalizedPublicationRecord(
            title="A Paper",
            year=2024,
            venue="CHI",
            url="https://doi.org/10.1/abc",
            source="openalex",
            source_author_id="https://openalex.org/A123",
            match_confidence=0.95,
        )
        issues = RecordValidator().validate_publications([record])
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
