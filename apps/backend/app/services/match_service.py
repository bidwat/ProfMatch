from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlmodel import select

from ..models.match import MatchEvidence, MatchScore, PublicationEvidence, StudentProfile
from ..models.professor import Professor, Publication

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "into", "using", "use", "uses", "about", "across", "via", "my", "i", "am", "is", "are", "be", "as",
    "research", "interested", "interest", "interests", "work", "working", "student", "phd", "ms", "masters",
}

ADJACENT_DEPARTMENTS = {
    "computer science": {"electrical engineering", "computer engineering", "data science", "information science", "statistics", "robotics"},
    "electrical engineering": {"computer science", "computer engineering", "robotics"},
    "data science": {"computer science", "statistics", "information science"},
    "robotics": {"computer science", "electrical engineering", "mechanical engineering"},
}


@dataclass
class Candidate:
    professor: Professor
    fts_score: float
    tags: list[str]
    publications: list[Publication]


class MatchService:
    def __init__(self, db: Session):
        self.db = db

    def find_matches(self, student: StudentProfile) -> List[MatchScore]:
        response = self.find_matches_with_metadata(student)
        return response["matches"]

    def find_matches_with_metadata(self, student: StudentProfile) -> dict[str, Any]:
        query_text = self._student_query_text(student)
        shortlist_limit = max(student.shortlist_limit, 30)
        candidates = self._fts_shortlist(query_text, shortlist_limit=shortlist_limit)

        if not candidates:
            candidates = self._fallback_shortlist(shortlist_limit)

        scores = [self._score_candidate(student, candidate) for candidate in candidates]
        scores.sort(key=lambda m: (m.total_score, m.fts_score, -m.professor_id), reverse=True)

        notes: list[str] = []
        rerank_model = None
        rerank_applied = False
        top_for_rerank = scores[: min(20, len(scores))]

        if student.rerank:
            self._load_openrouter_env()
            rerank_model = os.environ.get("OPENROUTER_MODEL", "inclusionai/ring-2.6-1t:free").strip()
            if not rerank_model.endswith(":free"):
                notes.append("LLM rerank skipped because OPENROUTER_MODEL must end with ':free' for this local MVP.")
            else:
                reranked = self._llm_rerank(student, top_for_rerank, rerank_model)
                id_to_match = {m.professor_id: m for m in scores}
                ordered: list[MatchScore] = []
                seen: set[int] = set()
                for item in reranked or []:
                    if not isinstance(item, dict):
                        continue
                    prof_id = self._safe_int(item.get("professor_id"))
                    match = id_to_match.get(prof_id) if prof_id is not None else None
                    if not match:
                        continue
                    match.llm_rerank_score = self._clamp01(self._safe_float(item.get("match_score"), match.total_score))
                    match.llm_rerank_reason = str(item.get("ranking_reason") or match.explanation)
                    risks = item.get("risks_uncertainties")
                    match.risks_uncertainties = [str(r) for r in risks] if isinstance(risks, list) else match.evidence.risks
                    outreach = item.get("suggested_outreach_angle")
                    match.suggested_outreach_angle = str(outreach) if outreach else None
                    match.rerank_applied = True
                    ordered.append(match)
                    seen.add(prof_id)
                if ordered:
                    rerank_applied = True
                    ordered.extend([m for m in scores if m.professor_id not in seen])
                    scores = ordered
                else:
                    notes.append("LLM rerank skipped or unavailable; returned deterministic FTS + metadata ranking.")

        limit = min(student.limit, 25)
        return {
            "matches": scores[:limit],
            "shortlist_size": len(candidates),
            "rerank_applied": rerank_applied,
            "rerank_model": rerank_model if rerank_applied else None,
            "notes": notes,
        }

    def _fts_shortlist(self, query_text: str, shortlist_limit: int) -> list[Candidate]:
        if self._dialect_name() != "sqlite":
            return self._portable_text_shortlist(query_text, shortlist_limit)

        self._ensure_fts_index()
        safe_query = self._fts_query(query_text)
        if not safe_query:
            return self._fallback_shortlist(shortlist_limit)

        sql = text(
            """
            SELECT professor_id, bm25(professor_match_fts, 8.0, 3.0, 2.0, 2.0, 6.0, 10.0, 5.0, 4.0, 7.0) AS rank
            FROM professor_match_fts
            WHERE professor_match_fts MATCH :query
            ORDER BY rank
            LIMIT :limit
            """
        )
        rows = self.db.execute(sql, {"query": safe_query, "limit": shortlist_limit}).fetchall()
        ranked_ids = [(int(r[0]), float(r[1])) for r in rows]
        if not ranked_ids:
            return []

        raw_scores = [rank for _, rank in ranked_ids]
        best = min(raw_scores)
        worst = max(raw_scores)
        spread = max(worst - best, 1e-9)
        normalized = {prof_id: max(0.0, min(1.0, 1.0 - ((rank - best) / spread))) for prof_id, rank in ranked_ids}

        return self._hydrate_candidates([prof_id for prof_id, _ in ranked_ids], normalized)

    def _dialect_name(self) -> str:
        bind = self.db.get_bind()
        return bind.dialect.name if bind is not None else "sqlite"

    def _portable_text_shortlist(self, query_text: str, shortlist_limit: int) -> list[Candidate]:
        """Database-portable shortlist for Postgres free-tier deployment.

        SQLite local dev uses FTS5. Production Postgres initially uses this
        deterministic in-process lexical shortlist so we can migrate without
        adding pg_trgm/tsvector migrations yet.
        """
        query_terms = self._extract_keywords(query_text)
        if not query_terms:
            return self._fallback_shortlist(shortlist_limit)
        professors = self.db.exec(select(Professor)).all()
        scored: list[tuple[int, float]] = []
        for prof in professors:
            if prof.id is None:
                continue
            tags = self._extract_tags(prof)
            text_value = " ".join([
                prof.name or "",
                prof.title or "",
                prof.department or "",
                prof.university or "",
                prof.research_text or "",
                prof.research_summary if self._has_meaningful_text(prof.research_summary) else "",
                " ".join(tags),
                prof.recruiting_evidence_text or "",
            ])
            prof_terms = self._extract_keywords(text_value)
            overlap = len(query_terms & prof_terms)
            if overlap == 0:
                continue
            score = self._jaccard_similarity(query_terms, prof_terms)
            if tags:
                score += min(0.08, 0.01 * len(tags))
            if self._has_meaningful_text(prof.research_summary):
                score += 0.04
            scored.append((int(prof.id), max(0.0, min(1.0, score))))
        scored.sort(key=lambda item: (item[1], -item[0]), reverse=True)
        ranked = scored[:shortlist_limit]
        return self._hydrate_candidates([prof_id for prof_id, _ in ranked], dict(ranked))

    def _fallback_shortlist(self, shortlist_limit: int) -> list[Candidate]:
        professors = self.db.exec(select(Professor).limit(shortlist_limit)).all()
        return self._hydrate_candidates([p.id for p in professors if p.id is not None], {})

    def _hydrate_candidates(self, professor_ids: list[int], fts_scores: dict[int, float]) -> list[Candidate]:
        if not professor_ids:
            return []
        professors = self.db.exec(select(Professor).where(Professor.id.in_(professor_ids))).all()
        by_id = {int(p.id): p for p in professors if p.id is not None}
        publications = (
            self.db.exec(
                select(Publication)
                .where(Publication.professor_id.in_(professor_ids))
                .order_by(Publication.year.desc(), Publication.title)
            ).all()
        )
        pubs_by_prof: dict[int, list[Publication]] = {pid: [] for pid in professor_ids}
        for pub in publications:
            pubs_by_prof.setdefault(pub.professor_id, []).append(pub)

        candidates: list[Candidate] = []
        for prof_id in professor_ids:
            prof = by_id.get(prof_id)
            if prof:
                candidates.append(Candidate(professor=prof, fts_score=fts_scores.get(prof_id, 0.0), tags=self._extract_tags(prof), publications=pubs_by_prof.get(prof_id, [])[:20]))
        return candidates

    def _ensure_fts_index(self) -> None:
        self.db.execute(text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS professor_match_fts USING fts5(
                professor_id UNINDEXED,
                name,
                title,
                department,
                university,
                research_text,
                research_summary,
                tags,
                recruiting_evidence_text
            )
            """
        ))
        # The local enrichment scripts update research_summary/tags directly in SQLite.
        # Rebuilding this small MVP index on each match request keeps FTS current without
        # requiring triggers or a migration framework yet.
        self.db.execute(text("DELETE FROM professor_match_fts"))
        rows = self.db.exec(select(Professor)).all()
        for prof in rows:
            tags = ", ".join(self._extract_tags(prof))
            self.db.execute(
                text(
                    """
                    INSERT INTO professor_match_fts(
                        professor_id, name, title, department, university, research_text,
                        research_summary, tags, recruiting_evidence_text
                    ) VALUES (:id, :name, :title, :department, :university, :research_text,
                        :research_summary, :tags, :recruiting_evidence_text)
                    """
                ),
                {
                    "id": prof.id,
                    "name": prof.name or "",
                    "title": prof.title or "",
                    "department": prof.department or "",
                    "university": prof.university or "",
                    "research_text": prof.research_text or "",
                    "research_summary": prof.research_summary if self._has_meaningful_text(prof.research_summary) else "",
                    "tags": tags,
                    "recruiting_evidence_text": prof.recruiting_evidence_text or "",
                },
            )
        self.db.commit()

    def _score_candidate(self, student: StudentProfile, candidate: Candidate) -> MatchScore:
        prof = candidate.professor
        student_terms = self._extract_keywords(self._student_query_text(student))
        research_text = " ".join([
            prof.name or "",
            prof.title or "",
            prof.department or "",
            prof.university or "",
            prof.research_text or "",
            prof.research_summary if self._has_meaningful_text(prof.research_summary) else "",
            " ".join(candidate.tags),
            prof.recruiting_evidence_text or "",
        ])
        selected_publications = self._select_relevant_publications(student_terms, candidate.publications, student.max_abstracts_per_professor)
        pub_text = " ".join([f"{item['publication'].title or ''} {item['publication'].abstract or ''} {item['publication'].venue or ''}" for item in selected_publications])

        research_sim = self._blend(candidate.fts_score, self._jaccard_similarity(student_terms, self._extract_keywords(research_text)), 0.75)
        if selected_publications:
            top_scores = [float(item["similarity_score"]) for item in selected_publications[:3]]
            pub_sim = sum(top_scores) / len(top_scores)
        else:
            pub_sim = 0.0
        recruit_score = self._recruiting_score(prof)
        dept_title = self._department_title_score(student, prof)
        location_fit = self._location_score(student, prof)
        metadata_boost = self._metadata_boost(prof, candidate, student)

        total = (
            0.45 * research_sim
            + 0.30 * pub_sim
            + 0.10 * recruit_score
            + 0.10 * dept_title
            + 0.05 * location_fit
            + metadata_boost
        )
        total = max(0.0, min(1.0, total))

        matched_terms = self._matched_terms(student_terms, research_text + " " + pub_text)
        photo = self._extract_photo(prof)
        evidence_publications = [
            PublicationEvidence(
                id=item["publication"].id,
                title=item["publication"].title,
                year=item["publication"].year,
                url=item["publication"].url,
                venue=item["publication"].venue,
                source=item["publication"].source,
                match_confidence=item["publication"].match_confidence,
                similarity_score=round(float(item["similarity_score"]), 4),
                matched_terms=item["matched_terms"],
                abstract=item["publication"].abstract,
                abstract_snippet=item["abstract_snippet"],
            )
            for item in selected_publications[:10]
        ] if student.include_publication_evidence else []
        evidence = MatchEvidence(
            matched_terms=matched_terms,
            tags=candidate.tags,
            publications=evidence_publications,
            recruiting_status=str(getattr(prof.recruiting_signal, "value", prof.recruiting_signal) or "unknown"),
            recruiting_evidence_url=prof.recruiting_evidence_url,
            recruiting_evidence_text=prof.recruiting_evidence_text,
            risks=self._risks(prof, candidate),
        )
        return MatchScore(
            professor_id=int(prof.id),
            professor_name=prof.name or "",
            title=prof.title,
            university=prof.university or "",
            department=prof.department or "",
            research_summary=prof.research_summary if self._has_meaningful_text(prof.research_summary) else None,
            professor_url=prof.homepage_url or prof.faculty_profile_url,
            photo_url=photo["photo_url"],
            photo_source_url=photo["photo_source_url"],
            photo_confidence=photo["photo_confidence"],
            total_score=round(total, 4),
            research_text_similarity=round(research_sim, 4),
            recent_publication_similarity=round(pub_sim, 4),
            recruiting_signal_score=round(recruit_score, 4),
            department_title_relevance=round(dept_title, 4),
            location_preference_fit=round(location_fit, 4),
            fts_score=round(candidate.fts_score, 4),
            metadata_boost=round(metadata_boost, 4),
            explanation=self._generate_explanation(student, prof, evidence),
            evidence=evidence,
        )

    def _select_relevant_publications(self, student_terms: set[str], publications: list[Publication], limit: int) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for pub in publications:
            title_terms = self._extract_keywords(pub.title or "")
            abstract_terms = self._extract_keywords(pub.abstract or "")
            venue_terms = self._extract_keywords(pub.venue or "")
            title_sim = self._jaccard_similarity(student_terms, title_terms)
            abstract_sim = self._jaccard_similarity(student_terms, abstract_terms) if abstract_terms else 0.0
            venue_sim = self._jaccard_similarity(student_terms, venue_terms) if venue_terms else 0.0
            if abstract_terms:
                score = (0.25 * title_sim) + (0.65 * abstract_sim) + (0.10 * venue_sim)
            else:
                score = (0.70 * title_sim) + (0.30 * venue_sim)
            if pub.year:
                score += max(0.0, min(0.04, (pub.year - 2018) * 0.006))
            score += max(0.0, min(0.03, (pub.match_confidence or 0.0) * 0.03))
            matched = sorted(student_terms & (title_terms | abstract_terms | venue_terms))[:10]
            if not matched and title_sim == 0.0 and abstract_sim == 0.0 and venue_sim == 0.0:
                continue
            ranked.append({
                "publication": pub,
                "similarity_score": max(0.0, min(1.0, score)),
                "matched_terms": matched,
                "abstract_snippet": self._abstract_snippet(pub.abstract, matched),
            })
        ranked.sort(key=lambda item: (float(item["similarity_score"]), int(item["publication"].year or 0), float(item["publication"].match_confidence or 0.0)), reverse=True)
        return ranked[: max(1, min(10, limit))]

    def _abstract_snippet(self, abstract: str | None, matched_terms: list[str]) -> str | None:
        text_value = (abstract or "").strip()
        if not text_value:
            return None
        lower = text_value.lower()
        start = 0
        for term in matched_terms:
            idx = lower.find(term.lower())
            if idx >= 0:
                start = max(0, idx - 90)
                break
        snippet = text_value[start:start + 320].strip()
        if start > 0:
            snippet = "…" + snippet
        if start + 320 < len(text_value):
            snippet += "…"
        return snippet

    def _extract_photo(self, prof: Professor) -> dict[str, Any]:
        extra = prof.extra or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}
        if not isinstance(extra, dict):
            extra = {}
        raw_url = extra.get("photo_url") or extra.get("image_url") or extra.get("profile_image_url") or extra.get("headshot_url")
        photo_url = str(raw_url).strip() if raw_url else None
        if photo_url and "default-profile-image" in photo_url.lower():
            photo_url = None
        source_url = extra.get("photo_source_url") or extra.get("image_source_url") or prof.faculty_profile_url or prof.homepage_url
        confidence = extra.get("photo_confidence") or extra.get("image_confidence")
        if photo_url and confidence is None:
            confidence = 0.75 if extra.get("image_source") == "university_profile" else 0.6
        return {
            "photo_url": photo_url,
            "photo_source_url": str(source_url).strip() if photo_url and source_url else None,
            "photo_confidence": float(confidence) if photo_url and confidence is not None else None,
        }

    def _llm_rerank(self, student: StudentProfile, matches: list[MatchScore], model: str) -> list[dict[str, Any]] | None:
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key or not matches:
            return None
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        prof_ids = [m.professor_id for m in matches]
        candidates = self._hydrate_candidates(prof_ids, {m.professor_id: m.fts_score for m in matches})
        prof_by_id = {c.professor.id: c for c in candidates}
        payload_candidates = []
        for m in matches:
            c = prof_by_id.get(m.professor_id)
            if not c:
                continue
            p = c.professor
            payload_candidates.append({
                "professor_id": p.id,
                "name": p.name,
                "title": p.title,
                "university": p.university,
                "department": p.department,
                "research_summary": ((p.research_summary if self._has_meaningful_text(p.research_summary) else None) or p.research_text or "")[:1400],
                "tags": c.tags,
                "recruiting_signal": str(getattr(p.recruiting_signal, "value", p.recruiting_signal) or "unknown"),
                "recruiting_evidence": (p.recruiting_evidence_text or "")[:500],
                "deterministic_score": m.total_score,
                "recent_publications": [{"title": pub.title, "year": pub.year, "abstract": (pub.abstract or "")[:500]} for pub in c.publications[:10]],
            })

        system = """You rerank professor-student research fit using only provided evidence. Return strict JSON only.
Do not claim a professor is recruiting unless recruiting evidence is present. Penalize weak/empty evidence.
JSON schema: {"matches":[{"professor_id":int,"match_score":0-1,"ranking_reason":str,"risks_uncertainties":[str],"suggested_outreach_angle":str}]}.
Return at most 5 matches in best-to-worst order."""
        user = json.dumps({"student_profile": student.model_dump(), "candidates": payload_candidates}, ensure_ascii=False)
        body = json.dumps({"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.2}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = self._parse_json_object(content)
            return parsed.get("matches") if isinstance(parsed.get("matches"), list) else None
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError):
            return None

    def _load_openrouter_env(self) -> None:
        env_path = Path(__file__).resolve().parents[4] / ".env.openrouter"
        if os.environ.get("OPENROUTER_API_KEY") or not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    def _student_query_text(self, student: StudentProfile) -> str:
        return " ".join(filter(None, [
            student.research_interests,
            student.background or "",
            student.target_degree or "",
            " ".join(student.preferred_departments or []),
            " ".join(student.preferred_universities or []),
            " ".join(student.preferred_locations or []),
        ]))

    def _extract_tags(self, prof: Professor) -> list[str]:
        extra = prof.extra or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except json.JSONDecodeError:
                extra = {}
        tags = extra.get("tags", []) if isinstance(extra, dict) else []
        return [str(t).strip() for t in tags if str(t).strip()]

    def _fts_query(self, text_value: str) -> str:
        terms = self._extract_keywords(text_value)
        return " OR ".join(f'"{term}"' for term in sorted(terms)[:24])

    def _extract_keywords(self, text_value: str) -> set[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}", (text_value or "").lower())
        return {w for w in words if w not in STOP_WORDS and len(w) > 2}

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    def _blend(self, a: float, b: float, a_weight: float) -> float:
        return max(0.0, min(1.0, (a_weight * a) + ((1 - a_weight) * b)))

    def _recruiting_score(self, prof: Professor) -> float:
        signal = str(getattr(prof.recruiting_signal, "value", prof.recruiting_signal) or "unknown")
        has_evidence = bool((prof.recruiting_evidence_text or "").strip() or (prof.recruiting_evidence_url or "").strip())
        if signal == "positive" and has_evidence:
            return 1.0
        if signal == "negative":
            return 0.0
        return 0.35

    def _department_title_score(self, student: StudentProfile, prof: Professor) -> float:
        score = 0.0
        dept = (prof.department or "").lower()
        title = (prof.title or "").lower()
        preferred = [d.lower() for d in (student.preferred_departments or [])]
        if preferred:
            if any(d in dept or dept in d for d in preferred):
                score += 0.55
            elif any(adj in dept for d in preferred for adj in ADJACENT_DEPARTMENTS.get(d, set())):
                score += 0.35
        elif "computer" in dept or "cs" == dept.strip():
            score += 0.4
        if "assistant professor" in title or "associate professor" in title:
            score += 0.35
        elif "professor" in title:
            score += 0.25
        if student.target_degree.lower() == "phd" and "lecturer" in title:
            score -= 0.25
        return max(0.0, min(1.0, score))

    def _location_score(self, student: StudentProfile, prof: Professor) -> float:
        university = (prof.university or "").lower()
        if student.preferred_universities and any(u.lower() in university or university in u.lower() for u in student.preferred_universities):
            return 1.0
        if student.preferred_locations and any(loc.lower() in university for loc in student.preferred_locations):
            return 0.7
        return 0.0

    def _metadata_boost(self, prof: Professor, candidate: Candidate, student: StudentProfile) -> float:
        boost = 0.0
        if self._has_meaningful_text(prof.research_summary):
            boost += 0.04
        if (prof.homepage_url or prof.faculty_profile_url):
            boost += 0.025
        if candidate.tags:
            boost += 0.025
        if candidate.publications:
            boost += min(0.04, len(candidate.publications) * 0.01)
        if (prof.source_confidence or 0.0) < 0.5:
            boost -= 0.06
        if not (prof.research_text or "").strip() and not self._has_meaningful_text(prof.research_summary):
            boost -= 0.08
        return max(-0.15, min(0.15, boost))

    def _has_meaningful_text(self, value: str | None) -> bool:
        text_value = (value or "").strip().lower()
        if not text_value:
            return False
        placeholders = {
            "research summary currently unavailable.",
            "research summary currently unavailable",
            "currently unavailable.",
            "currently unavailable",
        }
        return text_value not in placeholders

    def _matched_terms(self, student_terms: set[str], text_value: str) -> list[str]:
        haystack = self._extract_keywords(text_value)
        return sorted(student_terms & haystack)[:12]

    def _risks(self, prof: Professor, candidate: Candidate) -> list[str]:
        risks = []
        if not self._has_meaningful_text(prof.research_summary):
            risks.append("No synthesized research summary available.")
        if not candidate.publications:
            risks.append("No recent publication evidence available in the local database.")
        if str(getattr(prof.recruiting_signal, "value", prof.recruiting_signal) or "unknown") == "unknown":
            risks.append("Recruiting status is unknown.")
        if (prof.source_confidence or 0.0) < 0.5:
            risks.append("Source confidence is weak.")
        return risks

    def _generate_explanation(self, student: StudentProfile, prof: Professor, evidence: MatchEvidence) -> str:
        parts = []
        if evidence.matched_terms:
            parts.append(f"Research overlap includes {', '.join(evidence.matched_terms[:5])}.")
        if evidence.tags:
            parts.append(f"Profile tags include {', '.join(evidence.tags[:4])}.")
        if evidence.publications:
            pub = evidence.publications[0]
            parts.append(f"Recent publication evidence includes '{pub.title}'{f' ({pub.year})' if pub.year else ''}.")
        if evidence.recruiting_status == "positive" and (evidence.recruiting_evidence_text or evidence.recruiting_evidence_url):
            parts.append("There is explicit positive recruiting evidence.")
        elif evidence.recruiting_status == "unknown":
            parts.append("Recruiting status is unknown, so verify before outreach.")
        return " ".join(parts) or "Candidate was selected by local FTS search and metadata scoring."

    def _safe_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp01(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _parse_json_object(self, text_value: str) -> dict[str, Any]:
        cleaned = text_value.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)
