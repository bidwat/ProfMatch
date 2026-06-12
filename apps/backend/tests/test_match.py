import pytest
from pydantic import ValidationError

from apps.backend.app.db import MemoryDatabase
from apps.backend.app.models.match import StudentProfile
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication, RecruitingSignal
from apps.backend.app.services.match_service import MatchService


def _add_professor(db: MemoryDatabase, professor: Professor) -> int:
    return db.collection(PROFESSORS).add(professor.to_doc())


def test_two_stage_local_shortlist_scores_with_metadata(memory_db: MemoryDatabase):
    service = MatchService(memory_db)

    strong = Professor(
        name="Robotics ML Professor",
        normalized_name="robotics ml professor",
        university="Stanford University",
        department="Computer Science",
        research_text="Robot learning, machine learning, computer vision, and reinforcement learning for autonomy.",
        research_summary="Works on robot learning and vision-based autonomous systems.",
        recruiting_signal=RecruitingSignal.positive,
        recruiting_evidence_text="The lab is recruiting PhD students this cycle.",
        title="Assistant Professor",
        homepage_url="https://example.edu/lab",
        source_confidence=0.92,
        extra={"tags": ["Robotics", "Machine Learning", "Computer Vision"], "image_url": "https://example.edu/robotics.jpg", "image_source": "university_profile"},
    )
    weak = Professor(
        name="Systems Professor",
        normalized_name="systems professor",
        university="Another University",
        department="Computer Science",
        research_text="Distributed systems and databases.",
        research_summary="Works on systems.",
        recruiting_signal=RecruitingSignal.unknown,
        title="Professor",
        source_confidence=0.8,
        extra={"tags": ["Databases", "Distributed Systems"]},
    )
    strong_id = _add_professor(memory_db, strong)
    _add_professor(memory_db, weak)

    memory_db.collection(PUBLICATIONS).add(Publication(
        professor_id=strong_id,
        title="Robot Learning with Vision Foundation Models",
        year=2024,
        venue="Robotics Conference",
        abstract="Machine learning for robotics and computer vision.",
        source="test",
        match_confidence=0.95,
    ).to_doc())

    student = StudentProfile(
        name="Test Student",
        research_interests="robot learning machine learning computer vision",
        target_degree="PhD",
        preferred_universities=["Stanford University"],
        preferred_departments=["Computer Science"],
        rerank=False,
        limit=2,
    )

    result = service.find_matches_with_metadata(student)
    matches = result["matches"]

    assert result["shortlist_size"] >= 1
    assert matches[0].professor_id == strong_id
    assert matches[0].total_score > matches[-1].total_score
    assert matches[0].recruiting_signal_score == 1.0
    assert matches[0].location_preference_fit == 1.0
    assert "robotics" in [tag.lower() for tag in matches[0].evidence.tags]
    assert matches[0].evidence.publications[0].year == 2024
    assert matches[0].evidence.publications[0].similarity_score is not None
    assert "machine" in matches[0].evidence.publications[0].matched_terms
    assert matches[0].evidence.publications[0].abstract_snippet
    assert matches[0].photo_url == "https://example.edu/robotics.jpg"
    assert "Robot Learning with Vision Foundation Models" in matches[0].explanation
    assert "Research overlap includes" in matches[0].explanation


def test_research_interests_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        StudentProfile(research_interests="   ")


def test_recruiting_positive_requires_evidence(memory_db: MemoryDatabase):
    service = MatchService(memory_db)
    professor = Professor(
        name="No Evidence Professor",
        normalized_name="no evidence professor",
        university="Test University",
        department="Computer Science",
        research_text="Machine learning",
        research_summary="Machine learning",
        recruiting_signal=RecruitingSignal.positive,
        title="Assistant Professor",
        source_confidence=0.9,
    )
    _add_professor(memory_db, professor)

    assert service._recruiting_score(professor) == 0.35


def test_jaccard_similarity(memory_db: MemoryDatabase):
    service = MatchService(memory_db)
    assert service._jaccard_similarity({"a", "b"}, {"a", "c"}) == 1 / 3
    assert service._jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert service._jaccard_similarity(set(), set()) == 1.0
    assert service._jaccard_similarity({"a"}, set()) == 0.0
