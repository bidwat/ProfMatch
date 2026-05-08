from __future__ import annotations

from enum import Enum


class RecruitingSignal(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    UNIVERSITY_FACULTY_PAGE = "university_faculty_page"
    PROFESSOR_HOME_PAGE = "professor_homepage"
    OPENALEX = "openalex"
    DBLP = "dblp"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    GOOGLE_SCHOLAR = "google_scholar"


class DuplicateConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


SOURCE_PRIORITY = {
    SourceType.UNIVERSITY_FACULTY_PAGE: 1,
    SourceType.PROFESSOR_HOME_PAGE: 2,
    SourceType.OPENALEX: 3,
    SourceType.DBLP: 4,
    SourceType.SEMANTIC_SCHOLAR: 5,
    SourceType.GOOGLE_SCHOLAR: 6,
}

CONFIDENCE_THRESHOLDS = {
    "low": 0.4,
    "medium": 0.7,
    "high": 0.85,
}
