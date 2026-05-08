from __future__ import annotations

import unittest

from packages.scraper.core.models import ProfessorCandidate, PublicationCandidate
from packages.scraper.core.normalizer import ProfessorNormalizer, PublicationNormalizer


class NormalizerTests(unittest.TestCase):
    def test_professor_normalizer_sets_required_fields(self) -> None:
        candidate = ProfessorCandidate(
            name="Jane Doe",
            university="Stanford University",
            department="Computer Science",
            faculty_profile_url="https://example.edu/jane",
            source_url="https://example.edu/faculty",
            source_type="university_faculty_page",
            source_confidence=0.93,
            title="Assistant Professor",
            research_text="Human-computer interaction, augmented reality systems.",
            field_sources={"research_text": [{"source_type": "professor_homepage", "url": "https://example.edu/jane", "confidence": 0.8}]},
        )
        record = ProfessorNormalizer().normalize(candidate)
        self.assertEqual(record.name, "Jane Doe")
        self.assertEqual(record.normalized_name, "doe jane")
        self.assertEqual(record.recruiting_signal, "unknown")
        self.assertGreaterEqual(record.source_confidence, 0.9)
        self.assertIn("source_confidence", record.field_sources)
        self.assertTrue(record.research_summary.startswith("Human-computer"))

    def test_publication_normalizer_sets_required_fields(self) -> None:
        candidate = PublicationCandidate(
            title="Efficient Interactive Systems",
            year=2024,
            venue="CHI",
            url="https://doi.org/10.1/abc",
            source="openalex",
            source_author_id="https://openalex.org/A123",
            match_confidence=0.93,
        )
        record = PublicationNormalizer().normalize(candidate)
        self.assertEqual(record.source, "openalex")
        self.assertEqual(record.match_confidence, 0.93)
        self.assertEqual(record.title, "Efficient Interactive Systems")


if __name__ == "__main__":
    unittest.main()
