import base64
import json
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from apps.backend.app.models.professor import Professor, Publication


class ProfessorService:
    def __init__(self, session: Session):
        self.session = session

    def list_professors(
        self,
        q: Optional[str] = None,
        university: Optional[str | list[str]] = None,
        department: Optional[str | list[str]] = None,
        title: Optional[str] = None,
        tag: Optional[str | list[str]] = None,
        recruiting_signal: Optional[str] = None,
        sort: str = "name-asc",
        cursor: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        filters = []

        if q:
            search = f"%{q}%"
            filters.append(
                (Professor.name.ilike(search))
                | (Professor.title.ilike(search))
                | (Professor.department.ilike(search))
                | (Professor.university.ilike(search))
                | (Professor.research_text.ilike(search))
                | (Professor.research_summary.ilike(search))
            )

        if university:
            universities = [university] if isinstance(university, str) else [u for u in university if u]
            if universities:
                filters.append(Professor.university.in_(universities))

        if department:
            departments = [department] if isinstance(department, str) else [d for d in department if d]
            if departments:
                filters.append(Professor.department.in_(departments))

        if title:
            filters.append(Professor.title.ilike(f"%{title}%"))

        if recruiting_signal:
            filters.append(Professor.recruiting_signal == recruiting_signal)

        total_query = select(func.count(Professor.id)).where(*filters)
        total = int(self.session.exec(total_query).one() or 0)

        sort_columns = {
            "name": Professor.name,
            "university": Professor.university,
            "recruiting": Professor.recruiting_signal,
        }
        sort_key, _, sort_dir = sort.partition("-")
        sort_column = sort_columns.get(sort_key, Professor.name)
        order_by = sort_column.desc() if sort_dir == "desc" else sort_column.asc()

        offset = self._decode_cursor(cursor) if cursor else (page - 1) * limit
        if tag:
            tag_norms = [tag.strip().lower()] if isinstance(tag, str) else [t.strip().lower() for t in tag if t.strip()]
            all_for_tag = self.session.exec(select(Professor).where(*filters).order_by(order_by, Professor.id.asc())).all()
            tagged = [p for p in all_for_tag if all(t in [existing.lower() for existing in self._tags_for(p)] for t in tag_norms)]
            total = len(tagged)
            professors = tagged[offset:offset + limit]
        else:
            query = select(Professor).where(*filters).order_by(order_by, Professor.id.asc()).offset(offset).limit(limit)
            professors = self.session.exec(query).all()

        # Convert to summary
        professor_summaries = []
        for p in professors:
            extra = self._extra_for(p)
            tags = extra.get("tags", []) if isinstance(extra, dict) else []
            photo = self._extract_photo(extra, p.faculty_profile_url or p.homepage_url)
            publication_count = int(
                self.session.exec(
                    select(func.count(Publication.id)).where(Publication.professor_id == p.id)
                ).one() or 0
            )
            professor_summaries.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "title": p.title,
                    "university": p.university,
                    "department": p.department,
                    "research_summary": p.research_summary,
                    "recruiting_signal": p.recruiting_signal.value,
                    "source_confidence": p.source_confidence,
                    "publication_count": publication_count,
                    "tags": [str(t).strip() for t in tags if str(t).strip()],
                    "profile_display_status": extra.get("profile_display_status"),
                    "profile_text_source_url": extra.get("research_source_url") or extra.get("bio_source_url"),
                    "profile_text_confidence": extra.get("profile_text_confidence"),
                    "photo_url": photo["photo_url"],
                    "photo_source_url": photo["photo_source_url"],
                    "photo_confidence": photo["photo_confidence"],
                }
            )

        return {
            "professors": professor_summaries,
            "total": total,
            "page": page,
            "limit": limit,
            "next_cursor": self._encode_cursor(offset + len(professors)) if offset + len(professors) < total else None,
        }

    def list_facets(self) -> dict:
        professors = self.session.exec(select(Professor)).all()
        tags: set[str] = set()
        universities: set[str] = set()
        departments: set[str] = set()
        titles: set[str] = set()
        recruiting_signals: set[str] = set()
        for p in professors:
            if p.university:
                universities.add(p.university)
            if p.department:
                departments.add(p.department)
            if p.title:
                titles.add(p.title)
            if p.recruiting_signal:
                recruiting_signals.add(p.recruiting_signal.value)
            tags.update(self._tags_for(p))
        return {
            "tags": sorted(tags),
            "universities": sorted(universities),
            "departments": sorted(departments),
            "titles": sorted(titles),
            "recruiting_signals": sorted(recruiting_signals),
        }

    def list_indexed_groups(self) -> list[dict]:
        rows = self.session.exec(
            select(Professor.university, Professor.department, func.count(Professor.id))
            .group_by(Professor.university, Professor.department)
            .order_by(Professor.university, Professor.department)
        ).all()
        groups = []
        for university, department, professor_count in rows:
            publication_count = int(
                self.session.exec(
                    select(func.count(Publication.id))
                    .join(Professor, Publication.professor_id == Professor.id)
                    .where(Professor.university == university, Professor.department == department)
                ).one() or 0
            )
            groups.append({
                "university": university,
                "department": department,
                "professor_count": int(professor_count or 0),
                "publication_count": publication_count,
            })
        return groups

    def delete_indexed_group(self, university: str, department: str) -> dict:
        # Match trimmed + case-insensitively so rows that carry stray whitespace
        # or differ only by casing are still removed, and treat an empty/None
        # department symmetrically (a plain `== None` compiles to `= NULL`,
        # which never matches, silently deleting nothing).
        uni = (university or "").strip()
        dept = (department or "").strip()
        uni_match = func.lower(func.trim(Professor.university)) == uni.lower()
        if dept:
            dept_match = func.lower(func.trim(func.coalesce(Professor.department, ""))) == dept.lower()
        else:
            dept_match = func.trim(func.coalesce(Professor.department, "")) == ""
        professors = self.session.exec(
            select(Professor).where(uni_match, dept_match)
        ).all()
        ids = [p.id for p in professors if p.id is not None]
        deleted_publications = 0
        if ids:
            publications = self.session.exec(select(Publication).where(Publication.professor_id.in_(ids))).all()
            deleted_publications = len(publications)
            for pub in publications:
                self.session.delete(pub)
            for professor in professors:
                self.session.delete(professor)
            self.session.commit()
        return {"status": "deleted", "professors_deleted": len(ids), "publications_deleted": deleted_publications}

    def get_professor_by_id(self, professor_id: int) -> Optional[dict]:
        professor = self.session.get(Professor, professor_id)
        if not professor:
            return None

        publications_query = (
            select(Publication)
            .where(Publication.professor_id == professor_id)
            .order_by(Publication.year.desc(), Publication.title)
        )
        publications = self.session.exec(publications_query).all()

        publication_dicts = [
            {
                "id": p.id,
                "title": p.title,
                "year": p.year,
                "venue": p.venue,
                "abstract": p.abstract,
                "url": p.url,
                "source": p.source,
                "source_author_id": p.source_author_id,
                "match_confidence": p.match_confidence,
            }
            for p in publications
        ]

        extra = professor.extra or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}
        photo = self._extract_photo(extra, professor.faculty_profile_url or professor.homepage_url)

        professor_dict = {
            "id": professor.id,
            "name": professor.name,
            "normalized_name": professor.normalized_name,
            "title": professor.title,
            "university": professor.university,
            "department": professor.department,
            "email": professor.email,
            "faculty_profile_url": professor.faculty_profile_url,
            "homepage_url": professor.homepage_url,
            "google_scholar_url": professor.google_scholar_url,
            "openalex_id": professor.openalex_id,
            "dblp_url": professor.dblp_url,
            "semantic_scholar_id": professor.semantic_scholar_id,
            "research_text": professor.research_text,
            "research_summary": professor.research_summary,
            "recruiting_signal": professor.recruiting_signal.value,
            "recruiting_evidence_url": professor.recruiting_evidence_url,
            "recruiting_evidence_text": professor.recruiting_evidence_text,
            "source_confidence": professor.source_confidence,
            "created_at": professor.created_at.isoformat(),
            "updated_at": professor.updated_at.isoformat(),
            "photo_url": photo["photo_url"],
            "photo_source_url": photo["photo_source_url"],
            "photo_confidence": photo["photo_confidence"],
            "photo_license_note": photo["photo_license_note"],
            "extra": extra,
        }

        return {
            "professor": professor_dict,
            "publications": publication_dicts,
        }

    def _extract_photo(self, extra: dict, default_source_url: Optional[str]) -> dict:
        if not isinstance(extra, dict):
            extra = {}
        raw_url = (
            extra.get("photo_url")
            or extra.get("image_url")
            or extra.get("profile_image_url")
            or extra.get("headshot_url")
        )
        photo_url = str(raw_url).strip() if raw_url else None
        if photo_url and "default-profile-image" in photo_url.lower():
            photo_url = None
        source_url = (
            extra.get("photo_source_url")
            or extra.get("image_source_url")
            or default_source_url
        )
        confidence = extra.get("photo_confidence") or extra.get("image_confidence")
        if photo_url and confidence is None:
            confidence = 0.75 if extra.get("image_source") == "university_profile" else 0.6
        return {
            "photo_url": photo_url,
            "photo_source_url": str(source_url).strip() if photo_url and source_url else None,
            "photo_confidence": float(confidence) if photo_url and confidence is not None else None,
            "photo_license_note": extra.get("photo_license_note") or ("Public faculty/profile page image; verify reuse terms before redistribution." if photo_url else None),
        }

    def _extra_for(self, professor: Professor) -> dict:
        extra = professor.extra or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}
        return extra if isinstance(extra, dict) else {}

    def _tags_for(self, professor: Professor) -> list[str]:
        tags = self._extra_for(professor).get("tags", [])
        return [str(t).strip() for t in tags if str(t).strip()]

    def _encode_cursor(self, offset: int) -> str:
        return base64.urlsafe_b64encode(str(offset).encode()).decode()

    def _decode_cursor(self, cursor: str) -> int:
        try:
            return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
        except Exception:
            return 0