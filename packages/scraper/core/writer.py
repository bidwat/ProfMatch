from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .models import FetchResult, NormalizedProfessorRecord, NormalizedPublicationRecord, ScrapeRunRecord, SourceArtifact, ValidationIssue


class ArtifactWriter:
    def __init__(self, root: Path | str = Path(".")) -> None:
        self.root = Path(root)

    def raw_dir(self, artifact: SourceArtifact) -> Path:
        return (
            self.root
            / "data"
            / "raw"
            / artifact.university_slug
            / artifact.department_slug
            / artifact.adapter_name
            / artifact.run_id
        )

    def processed_dir(self, artifact: SourceArtifact) -> Path:
        return (
            self.root
            / "data"
            / "processed"
            / artifact.university_slug
            / artifact.department_slug
            / artifact.adapter_name
            / artifact.run_id
        )

    def write_fetch_result(self, fetch_result: FetchResult) -> Path:
        artifact = fetch_result.source_artifact
        raw_dir = self.raw_dir(artifact)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / artifact.artifact_name
        raw_path.write_text(fetch_result.body_text, encoding=artifact.encoding)
        manifest = raw_dir / "manifest.json"
        manifest.write_text(
            json.dumps({"artifact": artifact.to_dict(), "response_headers": fetch_result.response_headers}, indent=2),
            encoding="utf-8",
        )
        return raw_path

    def write_jsonl(self, path: Path, records: Sequence[dict]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def write_json(self, path: Path, data: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_processed_outputs(
        self,
        artifact: SourceArtifact,
        professors: Sequence[NormalizedProfessorRecord],
        publications: Sequence[NormalizedPublicationRecord],
        duplicates: Sequence[dict],
        validation: Sequence[ValidationIssue],
        run_record: ScrapeRunRecord,
    ) -> dict[str, Path]:
        processed_dir = self.processed_dir(artifact)
        paths = {
            "professors": self.write_jsonl(processed_dir / "professors.jsonl", [record.to_dict() for record in professors]),
            "publications": self.write_jsonl(processed_dir / "publications.jsonl", [record.to_dict() for record in publications]),
            "duplicates": self.write_jsonl(processed_dir / "duplicates.jsonl", duplicates),
            "validation": self.write_json(
                processed_dir / "validation.json",
                {
                    "issues": [issue.to_dict() for issue in validation],
                    "summary": {
                        "errors": sum(1 for issue in validation if issue.severity == "error"),
                        "warnings": sum(1 for issue in validation if issue.severity == "warning"),
                        "total": len(validation),
                    },
                },
            ),
            "scrape_run": self.write_json(processed_dir / "scrape_run.json", run_record.to_dict()),
        }
        return paths
