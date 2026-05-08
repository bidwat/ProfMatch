from __future__ import annotations

import unittest

from packages.scraper.core.models import ProfessorCandidate, PublicationCandidate, SourceArtifact


class ModelTests(unittest.TestCase):
    def test_source_artifact_serializes(self) -> None:
        artifact = SourceArtifact(
            run_id="run-1",
            university_slug="stanford-university",
            department_slug="computer-science",
            adapter_name="stanford",
            source_type="university_faculty_page",
            source_url="https://example.edu/faculty",
            artifact_name="roster.html",
            fetched_at="2026-04-26T00:00:00Z",
            status_code=200,
            content_type="text/html",
            content_hash="abc123",
            byte_count=10,
        )
        data = artifact.to_dict()
        self.assertEqual(data["artifact_name"], "roster.html")
        self.assertEqual(data["run_id"], "run-1")

    def test_candidate_serializes(self) -> None:
        candidate = ProfessorCandidate(
            name="Jane Doe",
            university="Stanford University",
            department="Computer Science",
            faculty_profile_url="https://example.edu/jane",
            source_url="https://example.edu/faculty",
            source_type="university_faculty_page",
            source_confidence=0.9,
        )
        self.assertEqual(candidate.to_dict()["name"], "Jane Doe")

    def test_publication_candidate_serializes(self) -> None:
        publication = PublicationCandidate(
            title="A Paper",
            year=2024,
            venue="CHI",
            url="https://doi.org/10.1/abc",
            source="openalex",
            source_author_id="https://openalex.org/A123",
            match_confidence=0.99,
        )
        self.assertEqual(publication.to_dict()["source"], "openalex")


if __name__ == "__main__":
    unittest.main()
