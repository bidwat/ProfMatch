import json
from pathlib import Path
from typing import Any, Optional

from apps.backend.app.db import Database
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication
from apps.backend.app.services.admin_scan_service import AdminScanService

PROFESSOR_UPDATE_FIELDS = [
    "name", "title", "department", "email", "faculty_profile_url", "homepage_url",
    "google_scholar_url", "openalex_id", "dblp_url", "semantic_scholar_id",
    "research_text", "research_summary", "recruiting_signal", "recruiting_evidence_url",
    "recruiting_evidence_text", "source_confidence", "extra",
]

PUBLICATION_UPDATE_FIELDS = ["venue", "url", "abstract", "source_author_id", "match_confidence"]


class ImportService:
    def __init__(self, db: Database, admin_service: AdminScanService):
        self.db = db
        self.admin_service = admin_service
        self.professors = db.collection(PROFESSORS)
        self.publications = db.collection(PUBLICATIONS)

    def import_scan(self, scan_id: str) -> dict[str, Any]:
        scan_detail = self.admin_service.get_scan(scan_id)
        if not scan_detail:
            raise ValueError(f"Scan {scan_id} not found")

        if not scan_detail.get("db_import_allowed"):
            raise ValueError(f"Scan {scan_id} is not approved for DB import")

        paths = scan_detail.get("paths", {})
        prof_path = paths.get("processed_professors")
        pub_path = paths.get("processed_publications")

        if not prof_path or not pub_path:
            raise ValueError("Processed artifact paths not found")

        from apps.backend.app.db import PROJECT_ROOT
        full_prof_path = PROJECT_ROOT / prof_path
        full_pub_path = PROJECT_ROOT / pub_path

        if not full_prof_path.exists() or not full_pub_path.exists():
            raise ValueError("Processed artifacts do not exist on disk")

        professors_data = self._read_jsonl(full_prof_path)
        publications_data = self._read_jsonl(full_pub_path)

        stats = {
            "professors_inserted": 0,
            "professors_updated": 0,
            "publications_inserted": 0,
            "publications_updated": 0,
            "errors": []
        }

        # map (normalized_name, university) -> professor id
        prof_map: dict[tuple, int] = {}

        for p_data in professors_data:
            try:
                prof_id = self._upsert_professor(p_data, stats)
                if prof_id:
                    key = (p_data.get("normalized_name"), p_data.get("university"))
                    prof_map[key] = prof_id
            except Exception as e:
                stats["errors"].append(f"Error importing professor {p_data.get('name')}: {str(e)}")

        for pub_data in publications_data:
            try:
                self._upsert_publication(pub_data, prof_map, stats)
            except Exception as e:
                stats["errors"].append(f"Error importing publication {pub_data.get('title')}: {str(e)}")

        report_path = self.admin_service.qa_dir / f"{scan_id}_import_report.json"
        report_path.write_text(json.dumps(stats, indent=2))

        return stats

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(line) for line in lines if line.strip()]

    def _find_professor(self, norm_name: Any, university: Any, faculty_url: Any) -> Optional[dict]:
        existing = next(
            (doc for doc in self.professors.find(normalized_name=norm_name) if doc.get("university") == university),
            None,
        )
        if not existing and faculty_url:
            existing = self.professors.find_one(faculty_profile_url=faculty_url)
        return existing

    def _upsert_professor(self, data: dict[str, Any], stats: dict[str, Any]) -> int:
        faculty_url = data.get("faculty_profile_url")
        norm_name = data.get("normalized_name")
        uni = data.get("university")

        existing = self._find_professor(norm_name, uni, faculty_url)

        if existing:
            patch = {key: data[key] for key in PROFESSOR_UPDATE_FIELDS if key in data}
            self.professors.update(existing["id"], patch)
            stats["professors_updated"] += 1
            return existing["id"]

        prof = Professor(
            name=data.get("name"),
            normalized_name=norm_name,
            title=data.get("title"),
            university=uni,
            department=data.get("department", ""),
            email=data.get("email"),
            faculty_profile_url=faculty_url,
            homepage_url=data.get("homepage_url"),
            google_scholar_url=data.get("google_scholar_url"),
            openalex_id=data.get("openalex_id"),
            dblp_url=data.get("dblp_url"),
            semantic_scholar_id=data.get("semantic_scholar_id"),
            research_text=data.get("research_text"),
            research_summary=data.get("research_summary"),
            recruiting_signal=data.get("recruiting_signal", "unknown"),
            recruiting_evidence_url=data.get("recruiting_evidence_url"),
            recruiting_evidence_text=data.get("recruiting_evidence_text"),
            source_confidence=data.get("source_confidence", 0.0),
            extra=data.get("extra", {})
        )
        stats["professors_inserted"] += 1
        return self.professors.add(prof.to_doc())

    def _upsert_publication(self, data: dict[str, Any], prof_map: dict, stats: dict[str, Any]) -> None:
        extra = data.get("extra", {})
        norm_name = extra.get("professor_normalized_name")
        uni = extra.get("professor_university")
        key = (norm_name, uni)

        prof_id = prof_map.get(key)
        if not prof_id:
            stats["errors"].append(f"Could not link publication '{data.get('title')}' to professor {norm_name} at {uni}")
            return

        title = data.get("title")
        year = data.get("year", 0)
        source = data.get("source", "unknown")

        existing = next(
            (
                doc for doc in self.publications.find(professor_id=prof_id, title=title)
                if doc.get("year") == year and doc.get("source") == source
            ),
            None,
        )

        if existing:
            patch = {field: data[field] for field in PUBLICATION_UPDATE_FIELDS if field in data}
            self.publications.update(existing["id"], patch)
            stats["publications_updated"] += 1
            return

        pub = Publication(
            professor_id=prof_id,
            title=title,
            year=year,
            venue=data.get("venue", ""),
            abstract=data.get("abstract"),
            url=data.get("url"),
            source=source,
            source_author_id=data.get("source_author_id"),
            match_confidence=data.get("match_confidence", 0.0)
        )
        self.publications.add(pub.to_doc())
        stats["publications_inserted"] += 1
