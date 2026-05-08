from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List
from urllib.parse import urlparse

from .models import NormalizedProfessorRecord
from .types import DuplicateConfidence
from ..sources.identifiers import canonicalize_url


@dataclass(slots=True)
class DuplicateCandidate:
    left_index: int
    right_index: int
    confidence: str
    score: float
    reasons: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "left_index": self.left_index,
            "right_index": self.right_index,
            "confidence": self.confidence,
            "score": self.score,
            "reasons": list(self.reasons),
        }


class DuplicateCandidateDetector:
    def detect(self, records: List[NormalizedProfessorRecord]) -> List[DuplicateCandidate]:
        duplicates: List[DuplicateCandidate] = []
        for i, left in enumerate(records):
            for j in range(i + 1, len(records)):
                right = records[j]
                score, reasons = self._score_pair(left, right)
                if score >= 0.75:
                    duplicates.append(
                        DuplicateCandidate(
                            left_index=i,
                            right_index=j,
                            confidence=self._bucket(score),
                            score=round(score, 3),
                            reasons=reasons,
                        )
                    )
        return duplicates

    def _score_pair(self, left: NormalizedProfessorRecord, right: NormalizedProfessorRecord) -> tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        if left.normalized_name == right.normalized_name:
            score += 0.4
            reasons.append("normalized name match")
        else:
            name_similarity = SequenceMatcher(None, left.normalized_name, right.normalized_name).ratio()
            score += name_similarity * 0.25
            if name_similarity >= 0.8:
                reasons.append("near name match")

        if left.university.lower() == right.university.lower():
            score += 0.25
            reasons.append("university match")
        if left.department.lower() == right.department.lower():
            score += 0.15
            reasons.append("department match")

        url_similarity = self._url_similarity(left.faculty_profile_url, right.faculty_profile_url)
        score += url_similarity * 0.2
        if url_similarity >= 0.7:
            reasons.append("URL overlap")

        return min(score, 1.0), reasons

    def _url_similarity(self, left_url: str, right_url: str) -> float:
        left = canonicalize_url(left_url)
        right = canonicalize_url(right_url)
        if left == right:
            return 1.0
        left_path = urlparse(left).path.rstrip("/")
        right_path = urlparse(right).path.rstrip("/")
        return SequenceMatcher(None, left_path, right_path).ratio()

    def _bucket(self, score: float) -> str:
        if score >= 0.85:
            return DuplicateConfidence.HIGH.value
        if score >= 0.7:
            return DuplicateConfidence.MEDIUM.value
        return DuplicateConfidence.LOW.value
