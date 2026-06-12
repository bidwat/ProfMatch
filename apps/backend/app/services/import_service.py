import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.services.admin_scan_service import AdminScanService


class ImportService:
    def __init__(self, session: Session, admin_service: AdminScanService):
        self.session = session
        self.admin_service = admin_service

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

        # map (normalized_name, university) -> Professor.id
        prof_map = {}

        # 1. Upsert Professors
        for p_data in professors_data:
            try:
                prof = self._upsert_professor(p_data, stats)
                if prof and prof.id:
                    key = (p_data.get("normalized_name"), p_data.get("university"))
                    prof_map[key] = prof.id
            except Exception as e:
                stats["errors"].append(f"Error importing professor {p_data.get('name')}: {str(e)}")

        # 2. Upsert Publications
        for pub_data in publications_data:
            try:
                self._upsert_publication(pub_data, prof_map, stats)
            except Exception as e:
                stats["errors"].append(f"Error importing publication {pub_data.get('title')}: {str(e)}")

        # 3. Write import report
        report_path = self.admin_service.qa_dir / f"{scan_id}_import_report.json"
        report_path.write_text(json.dumps(stats, indent=2))

        return stats

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(line) for line in lines if line.strip()]

    def _upsert_professor(self, data: dict[str, Any], stats: dict[str, Any]) -> Professor:
        faculty_url = data.get("faculty_profile_url")
        norm_name = data.get("normalized_name")
        uni = data.get("university")

        stmt = select(Professor).where(Professor.normalized_name == norm_name, Professor.university == uni)
        existing = self.session.exec(stmt).first()
        if not existing and faculty_url:
            stmt2 = select(Professor).where(Professor.faculty_profile_url == faculty_url)
            existing = self.session.exec(stmt2).first()

        if existing:
            # Update fields
            for key in ["name", "title", "department", "email", "faculty_profile_url", "homepage_url", 
                        "google_scholar_url", "openalex_id", "dblp_url", "semantic_scholar_id", 
                        "research_text", "research_summary", "recruiting_signal", "recruiting_evidence_url", 
                        "recruiting_evidence_text", "source_confidence", "extra"]:
                if key in data:
                    setattr(existing, key, data[key])
            stats["professors_updated"] += 1
            prof = existing
        else:
            # Insert
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
            self.session.add(prof)
            stats["professors_inserted"] += 1

        self.session.commit()
        self.session.refresh(prof)
        return prof

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

        stmt = select(Publication).where(
            Publication.professor_id == prof_id,
            Publication.title == title,
            Publication.year == year,
            Publication.source == source
        )
        existing = self.session.exec(stmt).first()

        if existing:
            for field in ["venue", "url", "abstract", "source_author_id", "match_confidence"]:
                if field in data:
                    setattr(existing, field, data[field])
            stats["publications_updated"] += 1
            pub = existing
        else:
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
            self.session.add(pub)
            stats["publications_inserted"] += 1

        self.session.commit()
