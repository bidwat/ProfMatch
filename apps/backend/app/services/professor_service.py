import base64
import json
from typing import Optional

from apps.backend.app.db import Database
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor


def _contains(haystack: Optional[str], needle: str) -> bool:
    return needle.lower() in (haystack or "").lower()


class ProfessorService:
    """Professor queries over the document store.

    The dataset is admin-curated and small (hundreds of professors), so list
    endpoints load the collection and filter/sort in process. Revisit with
    server-side Firestore queries if the dataset grows past that scale.
    """

    def __init__(self, db: Database):
        self.db = db
        self.professors = db.collection(PROFESSORS)
        self.publications = db.collection(PUBLICATIONS)

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
        professors = [Professor.from_doc(doc) for doc in self.professors.all()]

        if q:
            needle = q.strip()
            professors = [
                p for p in professors
                if any(
                    _contains(value, needle)
                    for value in (p.name, p.title, p.department, p.university, p.research_text, p.research_summary)
                )
            ]

        if university:
            universities = [university] if isinstance(university, str) else [u for u in university if u]
            if universities:
                professors = [p for p in professors if p.university in universities]

        if department:
            departments = [department] if isinstance(department, str) else [d for d in department if d]
            if departments:
                professors = [p for p in professors if p.department in departments]

        if title:
            professors = [p for p in professors if _contains(p.title, title)]

        if recruiting_signal:
            professors = [p for p in professors if p.recruiting_signal == recruiting_signal]

        if tag:
            tag_norms = [tag.strip().lower()] if isinstance(tag, str) else [t.strip().lower() for t in tag if t.strip()]
            professors = [
                p for p in professors
                if all(t in [existing.lower() for existing in self._tags_for(p)] for t in tag_norms)
            ]

        sort_key, _, sort_dir = sort.partition("-")
        key_funcs = {
            "name": lambda p: (p.name or "").lower(),
            "university": lambda p: (p.university or "").lower(),
            "recruiting": lambda p: p.recruiting_signal or "",
        }
        key_func = key_funcs.get(sort_key, key_funcs["name"])
        professors.sort(key=lambda p: (key_func(p), p.id or 0), reverse=(sort_dir == "desc"))

        total = len(professors)
        offset = self._decode_cursor(cursor) if cursor else (page - 1) * limit
        page_items = professors[offset:offset + limit]

        pub_counts = self._publication_counts()
        professor_summaries = []
        for p in page_items:
            extra = p.extra if isinstance(p.extra, dict) else {}
            tags = extra.get("tags", []) if isinstance(extra, dict) else []
            photo = self._extract_photo(extra, p.faculty_profile_url or p.homepage_url)
            professor_summaries.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "title": p.title,
                    "university": p.university,
                    "department": p.department,
                    "research_summary": p.research_summary,
                    "recruiting_signal": p.recruiting_signal,
                    "source_confidence": p.source_confidence,
                    "publication_count": pub_counts.get(p.id, 0),
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
            "next_cursor": self._encode_cursor(offset + len(page_items)) if offset + len(page_items) < total else None,
        }

    def list_facets(self) -> dict:
        professors = [Professor.from_doc(doc) for doc in self.professors.all()]
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
                recruiting_signals.add(p.recruiting_signal)
            tags.update(self._tags_for(p))
        return {
            "tags": sorted(tags),
            "universities": sorted(universities),
            "departments": sorted(departments),
            "titles": sorted(titles),
            "recruiting_signals": sorted(recruiting_signals),
        }

    def list_indexed_groups(self) -> list[dict]:
        pub_counts = self._publication_counts()
        groups: dict[tuple[str, str], dict] = {}
        for doc in self.professors.all():
            key = (doc.get("university") or "", doc.get("department") or "")
            group = groups.setdefault(key, {"university": key[0], "department": key[1], "professor_count": 0, "publication_count": 0})
            group["professor_count"] += 1
            group["publication_count"] += pub_counts.get(doc.get("id"), 0)
        return [groups[key] for key in sorted(groups)]

    def delete_indexed_group(self, university: str, department: str) -> dict:
        ids = [
            doc["id"] for doc in self.professors.all()
            if doc.get("university") == university and doc.get("department") == department and doc.get("id") is not None
        ]
        deleted_publications = 0
        if ids:
            id_set = set(ids)
            for pub in self.publications.all():
                if pub.get("professor_id") in id_set:
                    self.publications.delete(pub["id"])
                    deleted_publications += 1
            for prof_id in ids:
                self.professors.delete(prof_id)
        return {"status": "deleted", "professors_deleted": len(ids), "publications_deleted": deleted_publications}

    def get_professor_by_id(self, professor_id: int) -> Optional[dict]:
        doc = self.professors.get(professor_id)
        if not doc:
            return None
        professor = Professor.from_doc(doc)

        publications = [pub for pub in self.publications.find(professor_id=professor_id)]
        publications.sort(key=lambda p: (-(p.get("year") or 0), p.get("title") or ""))

        publication_dicts = [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "year": p.get("year"),
                "venue": p.get("venue"),
                "abstract": p.get("abstract"),
                "url": p.get("url"),
                "source": p.get("source"),
                "source_author_id": p.get("source_author_id"),
                "match_confidence": p.get("match_confidence"),
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
            "recruiting_signal": professor.recruiting_signal,
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

    def _publication_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for pub in self.publications.all():
            prof_id = pub.get("professor_id")
            if prof_id is not None:
                counts[prof_id] = counts.get(prof_id, 0) + 1
        return counts

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

    def _tags_for(self, professor: Professor) -> list[str]:
        extra = professor.extra if isinstance(professor.extra, dict) else {}
        tags = extra.get("tags", [])
        return [str(t).strip() for t in tags if str(t).strip()]

    def _encode_cursor(self, offset: int) -> str:
        return base64.urlsafe_b64encode(str(offset).encode()).decode()

    def _decode_cursor(self, cursor: str) -> int:
        try:
            return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
        except Exception:
            return 0
