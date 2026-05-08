import json
from pathlib import Path
from typing import Any, Optional

from apps.backend.app.db import PROJECT_ROOT


QA_SCAN_DIR = PROJECT_ROOT / "data" / "qa" / "scraper_runs"


def _safe_read_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive corruption path
        return {"status": "unreadable", "error": str(exc), "path": str(path)}


def _safe_read_jsonl_preview(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                records.append(json.loads(line))
                if len(records) >= limit:
                    break
    except Exception:
        pass
    return records


def _display_path(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    path = Path(value)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _issue_breakdown(issues: list[dict[str, Any]]) -> dict[str, Any]:
    missing: dict[str, int] = {}
    for issue in issues:
        if issue.get("code") != "missing_required_field":
            continue
        record_type = issue.get("record_type") or "record"
        field_name = issue.get("field_name") or "unknown"
        key = f"{record_type}.{field_name}"
        missing[key] = missing.get(key, 0) + 1
    return {
        "by_severity": _count_by(issues, "severity"),
        "by_code": _count_by(issues, "code"),
        "by_field": _count_by(issues, "field_name"),
        "by_record_type": _count_by(issues, "record_type"),
        "missing_required_fields": dict(sorted(missing.items())),
    }


def _truncate_records(records: Any, limit: int = 25) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        return []
    normalized = [record for record in records if isinstance(record, dict)]
    return normalized[:limit]


class AdminScanService:
    def __init__(self, qa_dir: Optional[Path] = None):
        self.qa_dir = qa_dir or QA_SCAN_DIR

    def list_scans(self) -> list[dict[str, Any]]:
        if not self.qa_dir.exists():
            return []
        rows = []
        for validation_path in sorted(self.qa_dir.glob("*_validation.json"), reverse=True):
            row = self._summary_from_validation(validation_path)
            if row:
                rows.append(row)
        return rows

    def get_scan(self, scan_id: str) -> Optional[dict[str, Any]]:
        for row in self.list_scans():
            if row["id"] == scan_id:
                validation_path = self.qa_dir / row["validation_filename"]
                manifest_path = self.qa_dir / row["manifest_filename"]
                audit_path = self.qa_dir / row["openrouter_audit_filename"]
                
                paths = row.get("paths", {})
                prof_path = paths.get("processed_professors")
                pub_path = paths.get("processed_publications")
                
                professors_preview = []
                if prof_path:
                    professors_preview = _safe_read_jsonl_preview(PROJECT_ROOT / prof_path, limit=50)
                    
                publications_preview = []
                if pub_path:
                    publications_preview = _safe_read_jsonl_preview(PROJECT_ROOT / pub_path, limit=50)

                return {
                    **row,
                    "validation": _safe_read_json(validation_path),
                    "scan_manifest": _safe_read_json(manifest_path),
                    "openrouter_audit": _safe_read_json(audit_path),
                    "issues_preview": _truncate_records((_safe_read_json(validation_path) or {}).get("issues"), limit=200),
                    "duplicate_candidates": _truncate_records((_safe_read_json(validation_path) or {}).get("duplicates"), limit=200),
                    "professors_preview": professors_preview,
                    "publications_preview": publications_preview,
                }
        return None

    def _summary_from_validation(self, validation_path: Path) -> Optional[dict[str, Any]]:
        validation = _safe_read_json(validation_path)
        if not validation:
            return None

        stem = validation_path.name.removesuffix("_validation.json")
        scan_id = stem
        manifest_filename = f"{stem}_scan_manifest.json"
        audit_filename = f"{stem}_openrouter_audit.json"
        manifest = _safe_read_json(self.qa_dir / manifest_filename) or {}
        audit = _safe_read_json(self.qa_dir / audit_filename) or {}

        run = validation.get("run") or {}
        summary = validation.get("summary") or {}
        issues = _truncate_records(validation.get("issues"), limit=500)
        duplicates = _truncate_records(validation.get("duplicates"), limit=100)
        artifact_paths = validation.get("artifact_paths") or {}
        artifacts = manifest.get("artifacts") or {}

        return {
            "id": scan_id,
            "date": stem.split("_", 1)[0] if "_" in stem else None,
            "school_slug": stem.split("_", 1)[1] if "_" in stem else stem,
            "university": run.get("university") or stem.split("_", 1)[-1].replace("-", " ").title(),
            "department": run.get("department"),
            "adapter_name": run.get("adapter_name"),
            "started_at": run.get("started_at"),
            "completed_at": run.get("completed_at"),
            "run_status": run.get("status"),
            "qa_status": validation.get("status"),
            "db_import_allowed": bool(validation.get("db_import_allowed")),
            "professors": int(summary.get("professors") or 0),
            "publications": int(summary.get("publications") or 0),
            "duplicates": int(summary.get("duplicates") or 0),
            "errors": int(summary.get("errors") or 0),
            "warnings": int(summary.get("warnings") or 0),
            "total_issues": int(summary.get("total_issues") or 0),
            "openrouter_status": audit.get("status"),
            "openrouter_model": audit.get("model"),
            "issue_breakdown": _issue_breakdown(issues),
            "issues_preview": issues[:25],
            "duplicate_candidates": duplicates[:25],
            "validation_filename": validation_path.name,
            "manifest_filename": manifest_filename,
            "openrouter_audit_filename": audit_filename,
            "paths": {
                "validation": _display_path(str(validation_path)),
                "scan_manifest": _display_path(str(self.qa_dir / manifest_filename)),
                "openrouter_audit": _display_path(str(self.qa_dir / audit_filename)),
                "raw": _display_path(artifact_paths.get("raw") or artifacts.get("raw")),
                "raw_manifest": _display_path(artifact_paths.get("raw_manifest")),
                "processed_professors": _display_path(artifact_paths.get("professors") or artifacts.get("processed_professors")),
                "processed_publications": _display_path(artifact_paths.get("publications") or artifacts.get("processed_publications")),
            },
        }
