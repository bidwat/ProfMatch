from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from packages.scraper.adapters import BerkeleyAdapter, CMUAdapter, StanfordAdapter
from packages.scraper.core.parser import FacultyRosterParser

FIXTURE = Path(__file__).parent / "fixtures" / "stanford_faculty_roster.html"


class AdapterTests(unittest.TestCase):
    def test_parser_extracts_candidates_from_fixture(self) -> None:
        html = FIXTURE.read_text(encoding="utf-8")
        candidates = FacultyRosterParser().parse_roster_html(
            html,
            source_url="https://www.cs.stanford.edu/people/faculty",
            university="Stanford University",
            department="Computer Science",
        )
        self.assertEqual(2, len(candidates))
        self.assertEqual("Jane Doe", candidates[0].name)
        self.assertEqual("https://www.cs.stanford.edu/people/jane-doe", candidates[0].faculty_profile_url)

    def test_stanford_adapter_runs_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outputs = StanfordAdapter().scrape(run_id="test-run", output_root=tmp, fixture_path=FIXTURE)
            self.assertEqual(2, len(outputs.professor_records))
            self.assertTrue(outputs.raw_path.exists())
            self.assertTrue(outputs.processed_paths["professors"].exists())
            self.assertEqual("success", outputs.run_record.status)
            self.assertEqual(0, len(outputs.duplicates))

    def test_seed_adapters_exist(self) -> None:
        self.assertEqual("cmu", CMUAdapter().adapter_name)
        self.assertEqual("berkeley", BerkeleyAdapter().adapter_name)


if __name__ == "__main__":
    unittest.main()
