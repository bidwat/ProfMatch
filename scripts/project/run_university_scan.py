#!/usr/bin/env python3
"""Run a safe, auditable university faculty scan.

This is the Phase 3 workflow wrapper around existing scraper adapters. It keeps
legacy adapter outputs intact, then writes the canonical scan artifacts expected
by Professor Match:

  data/raw/university_scans/{date}/{school}/...
  data/processed/university_scans/{date}/{school}_professors.jsonl
  data/processed/university_scans/{date}/{school}_publications.jsonl
  data/qa/scraper_runs/{date}_{school}_validation.json

The command does not import into SQLite. DB import remains a separate explicit
step after QA review.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.scraper.sources.identifiers import slugify

ADAPTERS = {
    "berkeley": "packages.scraper.adapters.berkeley:BerkeleyAdapter",
    "cmu": "packages.scraper.adapters.cmu:CMUAdapter",
    "cornell": "packages.scraper.adapters.cornell:CornellAdapter",
    "georgia-tech": "packages.scraper.adapters.georgia_tech:GeorgiaTechAdapter",
    "michigan": "packages.scraper.adapters.michigan:MichiganAdapter",
    "mit": "packages.scraper.adapters.mit:MITAdapter",
    "stanford": "packages.scraper.adapters.stanford:StanfordAdapter",
    "uiuc": "packages.scraper.adapters.uiuc:UIUCAdapter",
    "ut-austin": "packages.scraper.adapters.ut_austin:UTAustinAdapter",
    "washington": "packages.scraper.adapters.washington:WashingtonAdapter",
    "tamu_cse": "packages.scraper.adapters.tamu_cse:TamuCseAdapter",
}


def load_adapter(adapter_name: str):
    module_name, class_name = ADAPTERS[adapter_name].split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Professor Match university scan and write auditable artifacts.")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--fixture", type=Path, help="Offline HTML fixture to parse instead of fetching live source.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--date", type=str, default=None, help="Artifact date folder, default YYYY-MM-DD in UTC.")
    parser.add_argument("--enrich-profiles", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enrich-publications", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--openrouter-extract",
        action="store_true",
        help="Record an OpenRouter extraction audit stub. Actual extraction requires a BYO key and a :free model.",
    )
    return parser


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _copy_or_write_jsonl(source: Path, dest: Path, records: list[dict[str, Any]] | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copyfile(source, dest)
    else:
        with dest.open("w", encoding="utf-8") as fh:
            for record in records or []:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return dest


def _openrouter_audit(*, enabled: bool, raw_path: Path, output_root: Path, date_slug: str, school_slug: str) -> Path:
    model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash:free").strip()
    has_key = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
    status = "disabled"
    reason = "openrouter extraction flag was not provided"
    if enabled:
        if not has_key:
            status = "skipped"
            reason = "OPENROUTER_API_KEY is not set"
        elif not model.endswith(":free"):
            status = "skipped"
            reason = "OPENROUTER_MODEL must end with ':free' for this local MVP"
        else:
            status = "ready_not_executed"
            reason = "audit foundation is present; extraction implementation is intentionally gated"
    path = output_root / "data" / "qa" / "scraper_runs" / f"{date_slug}_{school_slug}_openrouter_audit.json"
    return _write_json(
        path,
        {
            "status": status,
            "reason": reason,
            "model": model if enabled else None,
            "input_path": str(raw_path),
            "prompt_version": "university_scan_extraction_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rules": [
                "Use only saved source text/HTML as input.",
                "Return strict JSON with evidence snippets and confidence.",
                "Never invent professor records, emails, profile URLs, or recruiting status.",
                "Persist prompt, model, input path, output, and timestamp before DB import.",
            ],
        },
    )


def run_scan(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve()
    date_slug = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    adapter = load_adapter(args.adapter)()
    school_slug = slugify(adapter.university)

    outputs = adapter.scrape(
        run_id=args.run_id,
        output_root=output_root,
        fixture_path=args.fixture,
        enrich_profiles=args.enrich_profiles,
        enrich_publications=args.enrich_publications,
    )

    raw_dir = output_root / "data" / "raw" / "university_scans" / date_slug / school_slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical_raw_path = raw_dir / outputs.raw_path.name
    shutil.copyfile(outputs.raw_path, canonical_raw_path)
    canonical_raw_manifest = _write_json(
        raw_dir / "manifest.json",
        {
            "run_id": outputs.run_record.run_id,
            "adapter": adapter.adapter_name,
            "university": adapter.university,
            "department": adapter.department,
            "source_urls": outputs.run_record.source_urls,
            "legacy_raw_path": str(outputs.raw_path),
            "canonical_raw_path": str(canonical_raw_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    processed_dir = output_root / "data" / "processed" / "university_scans" / date_slug
    professor_records = [record.to_dict() for record in outputs.professor_records]
    publication_records = [record.to_dict() for record in outputs.publication_records]
    canonical_professors = _copy_or_write_jsonl(
        outputs.processed_paths.get("professors", Path()),
        processed_dir / f"{school_slug}_professors.jsonl",
        professor_records,
    )
    canonical_publications = _copy_or_write_jsonl(
        outputs.processed_paths.get("publications", Path()),
        processed_dir / f"{school_slug}_publications.jsonl",
        publication_records,
    )

    issues = [issue.to_dict() for issue in outputs.validation_issues]
    errors = [issue for issue in issues if issue.get("severity") == "error"]
    warnings = [issue for issue in issues if issue.get("severity") == "warning"]
    qa_path = _write_json(
        output_root / "data" / "qa" / "scraper_runs" / f"{date_slug}_{school_slug}_validation.json",
        {
            "run": outputs.run_record.to_dict(),
            "status": "blocked" if errors else "ready_for_review",
            "summary": {
                "professors": len(professor_records),
                "publications": len(publication_records),
                "duplicates": len(outputs.duplicates),
                "errors": len(errors),
                "warnings": len(warnings),
                "total_issues": len(issues),
            },
            "issues": issues,
            "duplicates": outputs.duplicates,
            "artifact_paths": {
                "raw": str(canonical_raw_path),
                "raw_manifest": str(canonical_raw_manifest),
                "professors": str(canonical_professors),
                "publications": str(canonical_publications),
            },
            "db_import_allowed": not errors,
        },
    )
    openrouter_audit = _openrouter_audit(
        enabled=args.openrouter_extract,
        raw_path=canonical_raw_path,
        output_root=output_root,
        date_slug=date_slug,
        school_slug=school_slug,
    )
    manifest_path = _write_json(
        output_root / "data" / "qa" / "scraper_runs" / f"{date_slug}_{school_slug}_scan_manifest.json",
        {
            "pipeline": [
                "seed URL",
                "fetch raw source",
                "save raw HTML/payload",
                "deterministic parser",
                "optional OpenRouter extraction from saved source text",
                "normalize",
                "validate",
                "write processed JSON",
                "QA gate",
                "optional DB import",
            ],
            "artifacts": {
                "raw": str(canonical_raw_path),
                "processed_professors": str(canonical_professors),
                "processed_publications": str(canonical_publications),
                "qa_validation": str(qa_path),
                "openrouter_audit": str(openrouter_audit),
            },
            "import_policy": "No SQLite import is performed by this scan command; import requires separate QA approval.",
        },
    )

    return {
        "adapter": args.adapter,
        "run_id": outputs.run_record.run_id,
        "status": "blocked" if errors else "ready_for_review",
        "professor_count": len(professor_records),
        "publication_count": len(publication_records),
        "duplicate_count": len(outputs.duplicates),
        "validation_error_count": len(errors),
        "validation_warning_count": len(warnings),
        "artifacts": {
            "raw": str(canonical_raw_path),
            "professors": str(canonical_professors),
            "publications": str(canonical_publications),
            "qa_validation": str(qa_path),
            "scan_manifest": str(manifest_path),
            "openrouter_audit": str(openrouter_audit),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_scan(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"ready_for_review", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
