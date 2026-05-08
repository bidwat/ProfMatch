from __future__ import annotations

import unittest
from unittest.mock import Mock

from packages.scraper.core.enrichers.dblp import DBLPEnricher
from packages.scraper.core.enrichers.google_scholar import GoogleScholarLinkExtractor
from packages.scraper.core.enrichers.openalex import OpenAlexEnricher
from packages.scraper.core.enrichers.semanticscholar import SemanticScholarEnricher


def _mock_response(payload: dict) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


class EnricherTests(unittest.TestCase):
    def test_openalex_normalization(self) -> None:
        result = OpenAlexEnricher().normalize_author_payload(
            {
                "works": [
                    {
                        "title": "A Paper",
                        "publication_year": 2024,
                        "primary_location": {"source": {"display_name": "CHI"}},
                        "doi": "https://doi.org/10.1/abc",
                        "cited_by_count": 4,
                        "authorships": [{"author": {"display_name": "Jane Doe"}}],
                        "id": "https://openalex.org/W1",
                    }
                ]
            },
            source_author_id="https://openalex.org/A123",
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.records[0]["source"], "openalex")

    def test_openalex_enrich_by_author_name(self) -> None:
        enricher = OpenAlexEnricher(min_delay_seconds=0)
        enricher.session.get = Mock(
            side_effect=[
                _mock_response({"results": [{"id": "https://openalex.org/A123", "display_name": "Jane Doe"}]}),
                _mock_response(
                    {
                        "results": [
                            {
                                "title": "A Paper",
                                "publication_year": 2024,
                                "primary_location": {"source": {"display_name": "CHI"}},
                                "doi": "https://doi.org/10.1/abc",
                            }
                        ]
                    }
                ),
            ]
        )

        result = enricher.enrich_by_author_name("Jane Doe", max_publications=2)
        self.assertTrue(result.matched)
        self.assertEqual("openalex", result.source)
        self.assertEqual(1, len(result.records))

    def test_dblp_normalization(self) -> None:
        result = DBLPEnricher().normalize_publications(
            [{"title": "A Paper", "year": 2024, "venue": "CHI", "ee": "https://doi.org/10.1/abc"}],
            source_author_id="pid/123",
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.records[0]["source"], "dblp")

    def test_dblp_enrich_by_author_name(self) -> None:
        enricher = DBLPEnricher(min_delay_seconds=0)
        enricher.session.get = Mock(
            side_effect=[
                _mock_response(
                    {
                        "result": {
                            "hits": {
                                "hit": [
                                    {
                                        "info": {
                                            "author": "Jane Doe",
                                            "url": "https://dblp.org/pid/12/3456.html",
                                        }
                                    }
                                ]
                            }
                        }
                    }
                ),
                _mock_response(
                    {
                        "dblpperson": {
                            "r": [
                                {
                                    "article": {
                                        "info": {
                                            "title": "A Paper",
                                            "year": "2024",
                                            "venue": "CHI",
                                            "ee": "https://doi.org/10.1/abc",
                                            "authors": {"author": ["Jane Doe", "John Roe"]},
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ),
            ]
        )

        result = enricher.enrich_by_author_name("Jane Doe", max_publications=2)
        self.assertTrue(result.matched)
        self.assertEqual("dblp", result.source)
        self.assertEqual(1, len(result.records))

    def test_semantic_scholar_normalization(self) -> None:
        result = SemanticScholarEnricher().normalize_paper(
            {"title": "A Paper", "year": 2024, "venue": "CHI", "citationCount": 12, "paperId": "S2-123"},
            source_author_id="https://example.edu/jane",
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.records[0]["source"], "semantic_scholar")

    def test_semantic_scholar_enrich_by_author_name(self) -> None:
        enricher = SemanticScholarEnricher(min_delay_seconds=0)
        enricher.session.get = Mock(
            side_effect=[
                _mock_response({"data": [{"authorId": "145", "name": "Jane Doe"}]}),
                _mock_response(
                    {
                        "data": [
                            {
                                "title": "A Paper",
                                "year": 2024,
                                "venue": "CHI",
                                "paperId": "S2-123",
                                "authors": [{"name": "Jane Doe"}],
                            }
                        ]
                    }
                ),
            ]
        )

        result = enricher.enrich_by_author_name("Jane Doe", max_publications=2)
        self.assertTrue(result.matched)
        self.assertEqual("semantic_scholar", result.source)
        self.assertEqual(1, len(result.records))

    def test_google_scholar_link_extractor(self) -> None:
        url = GoogleScholarLinkExtractor().extract_profile_url("See https://scholar.google.com/citations?user=abc123 for details.")
        self.assertEqual(url, "https://scholar.google.com/citations?user=abc123")


if __name__ == "__main__":
    unittest.main()
