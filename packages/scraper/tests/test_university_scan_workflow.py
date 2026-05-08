from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.project.run_university_scan import main

FIXTURE = Path(__file__).parent / "fixtures" / "stanford_faculty_roster.html"


class UniversityScanWorkflowTests(unittest.TestCase):
    def test_scan_workflow_writes_canonical_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                code = main([
                    "--adapter", "stanford",
                    "--fixture", str(FIXTURE),
                    "--run-id", "scan-test",
                    "--output-root", tmp,
                    "--date", "2026-04-30",
                    "--no-enrich-profiles",
                    "--no-enrich-publications",
                ])
            self.assertEqual(0, code)
            root = Path(tmp)
            raw_path = root / "data" / "raw" / "university_scans" / "2026-04-30" / "stanford-university" / "roster.html"
            professors_path = root / "data" / "processed" / "university_scans" / "2026-04-30" / "stanford-university_professors.jsonl"
            publications_path = root / "data" / "processed" / "university_scans" / "2026-04-30" / "stanford-university_publications.jsonl"
            qa_path = root / "data" / "qa" / "scraper_runs" / "2026-04-30_stanford-university_validation.json"
            manifest_path = root / "data" / "qa" / "scraper_runs" / "2026-04-30_stanford-university_scan_manifest.json"
            audit_path = root / "data" / "qa" / "scraper_runs" / "2026-04-30_stanford-university_openrouter_audit.json"

            for path in [raw_path, professors_path, publications_path, qa_path, manifest_path, audit_path]:
                self.assertTrue(path.exists(), f"missing {path}")

            professor_lines = [line for line in professors_path.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(2, len(professor_lines))

            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual("ready_for_review", qa["status"])
            self.assertEqual(2, qa["summary"]["professors"])
            self.assertTrue(qa["db_import_allowed"])

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("QA gate", manifest["pipeline"])
            self.assertIn("No SQLite import", manifest["import_policy"])

            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual("disabled", audit["status"])


if __name__ == "__main__":
    unittest.main()
