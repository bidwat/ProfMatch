from __future__ import annotations

import unittest

from packages.scraper.core.deduper import DuplicateCandidateDetector
from packages.scraper.core.models import NormalizedProfessorRecord


class DeduperTests(unittest.TestCase):
    def test_detects_high_confidence_duplicate(self) -> None:
        records = [
            NormalizedProfessorRecord(
                name="Jane Doe",
                normalized_name="doe jane",
                university="Stanford University",
                department="Computer Science",
                faculty_profile_url="https://cs.stanford.edu/people/jane-doe",
                source_confidence=0.91,
            ),
            NormalizedProfessorRecord(
                name="Jane Doe",
                normalized_name="doe jane",
                university="Stanford University",
                department="Computer Science",
                faculty_profile_url="https://cs.stanford.edu/people/jane-doe/",
                source_confidence=0.88,
            ),
        ]
        duplicates = DuplicateCandidateDetector().detect(records)
        self.assertEqual(1, len(duplicates))
        self.assertEqual("high", duplicates[0].confidence)

    def test_does_not_flag_unrelated_records(self) -> None:
        records = [
            NormalizedProfessorRecord(
                name="Jane Doe",
                normalized_name="doe jane",
                university="Stanford University",
                department="Computer Science",
                faculty_profile_url="https://cs.stanford.edu/people/jane-doe",
                source_confidence=0.91,
            ),
            NormalizedProfessorRecord(
                name="Alan Turing",
                normalized_name="turing alan",
                university="MIT",
                department="Mathematics",
                faculty_profile_url="https://mit.edu/alan",
                source_confidence=0.85,
            ),
        ]
        duplicates = DuplicateCandidateDetector().detect(records)
        self.assertEqual([], duplicates)


if __name__ == "__main__":
    unittest.main()
