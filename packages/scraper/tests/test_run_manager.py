from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packages.scraper.adapters.stanford import StanfordAdapter
from packages.scraper.core.models import EnrichmentResult
from packages.scraper.core.run_manager import ScrapeRunManager

FIXTURE = Path(__file__).parent / "fixtures" / "stanford_faculty_roster.html"


class FakeOpenAlexEnricher:
    source_name = "openalex"

    def enrich_by_author_name(self, author_name: str, *, max_publications: int = 3) -> EnrichmentResult:  # noqa: ARG002
        return EnrichmentResult(
            source="openalex",
            matched=True,
            confidence=0.9,
            source_author_id=f"A-{author_name.lower().replace(' ', '-')}",
            source_url="https://api.openalex.org/authors/mock",
            records=[
                {
                    "title": f"{author_name} Publication",
                    "year": 2024,
                    "venue": "TestConf",
                    "url": "https://doi.org/10.0/mock",
                    "source": "openalex",
                    "source_author_id": f"A-{author_name.lower().replace(' ', '-')}",
                    "match_confidence": 0.9,
                }
            ],
        )


class FakeNoMatchEnricher:
    source_name = "dblp"

    def enrich_by_author_name(self, author_name: str, *, max_publications: int = 3) -> EnrichmentResult:  # noqa: ARG002
        return EnrichmentResult(
            source="dblp",
            matched=False,
            confidence=0.0,
            reason="No DBLP publications found",
            records=[],
        )


class RunManagerPublicationTests(unittest.TestCase):
    def test_run_manager_enriches_publications_and_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = ScrapeRunManager(publication_enrichers=[FakeOpenAlexEnricher(), FakeNoMatchEnricher()])
            adapter = StanfordAdapter()
            outputs = manager.run_adapter(
                adapter,
                run_id="test-publications",
                output_root=tmp,
                fixture_path=FIXTURE,
                enrich_publications=True,
            )

            self.assertGreater(len(outputs.professor_records), 0)
            self.assertGreater(len(outputs.publication_records), 0)
            for professor in outputs.professor_records:
                self.assertGreaterEqual(len(professor.publications), 1)
                self.assertIn("publication_enrichment", professor.extra)
                self.assertTrue(any(item.get("source") == "dblp" for item in professor.extra["publication_enrichment"]))

            publications_path = outputs.processed_paths["publications"]
            self.assertTrue(publications_path.exists())
            lines = [line for line in publications_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreater(len(lines), 0)


if __name__ == "__main__":
    unittest.main()
