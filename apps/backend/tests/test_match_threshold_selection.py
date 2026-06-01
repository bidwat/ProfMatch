from apps.backend.app.models.match import MatchEvidence, MatchScore
from apps.backend.app.services.match_service import select_matches_by_threshold


def make_match(professor_id: int, score: float) -> MatchScore:
    return MatchScore(
        professor_id=professor_id,
        professor_name=f"Professor {professor_id}",
        university="Test University",
        department="Computer Science",
        total_score=score,
        research_text_similarity=score,
        recent_publication_similarity=0.0,
        recruiting_signal_score=0.0,
        department_title_relevance=0.0,
        location_preference_fit=0.0,
        explanation="test",
        evidence=MatchEvidence(),
    )


def test_threshold_falls_back_to_top_10_when_fewer_above_threshold():
    matches = [make_match(i, score) for i, score in enumerate([0.9, 0.8, 0.7, 0.6, 0.39, 0.38, 0.37, 0.36, 0.35, 0.34, 0.33, 0.32], 1)]

    selected, metadata = select_matches_by_threshold(matches, threshold_percent=40, minimum_results=10)

    assert [match.professor_id for match in selected] == list(range(1, 11))
    assert metadata["above_threshold_count"] == 4
    assert metadata["returned_count"] == 10
    assert metadata["fallback_top_results_used"] is True


def test_threshold_returns_exact_10_without_fallback():
    matches = [make_match(i, 0.5 if i <= 10 else 0.39) for i in range(1, 21)]

    selected, metadata = select_matches_by_threshold(matches, threshold_percent=40, minimum_results=10)

    assert len(selected) == 10
    assert metadata["above_threshold_count"] == 10
    assert metadata["fallback_top_results_used"] is False


def test_threshold_returns_all_above_threshold():
    matches = [make_match(i, 0.5 if i <= 25 else 0.39) for i in range(1, 31)]

    selected, metadata = select_matches_by_threshold(matches, threshold_percent=40, minimum_results=10)

    assert len(selected) == 25
    assert selected[-1].professor_id == 25
    assert metadata["returned_count"] == 25
    assert metadata["fallback_top_results_used"] is False


def test_higher_threshold_keeps_top_10_fallback():
    matches = [make_match(i, score) for i, score in enumerate([0.95, 0.82, 0.71, 0.69, 0.60, 0.55, 0.50, 0.45, 0.42, 0.40, 0.35], 1)]

    selected, metadata = select_matches_by_threshold(matches, threshold_percent=70, minimum_results=10)

    assert [match.professor_id for match in selected] == list(range(1, 11))
    assert metadata["above_threshold_count"] == 3
    assert metadata["fallback_top_results_used"] is True


def test_fractional_scores_are_interpreted_as_percentages():
    selected, metadata = select_matches_by_threshold([make_match(1, 0.42), make_match(2, 0.39)], threshold_percent=40, minimum_results=1)

    assert [match.professor_id for match in selected] == [1]
    assert metadata["above_threshold_count"] == 1


def test_0_to_100_scores_are_interpreted_as_percentages():
    selected, metadata = select_matches_by_threshold([make_match(1, 42), make_match(2, 39)], threshold_percent=40, minimum_results=1)

    assert [match.professor_id for match in selected] == [1]
    assert metadata["above_threshold_count"] == 1


def test_rank_order_is_preserved_for_threshold_union():
    matches = [make_match(i, score) for i, score in enumerate([0.95, 0.39, 0.85, 0.38, 0.75, 0.37], 1)]

    selected, _ = select_matches_by_threshold(matches, threshold_percent=40, minimum_results=2)

    assert [match.professor_id for match in selected] == [1, 2, 3, 5]


def test_duplicate_matches_are_not_returned_when_fallback_overlaps_threshold():
    matches = [make_match(i, 0.8 if i <= 3 else 0.3) for i in range(1, 8)]

    selected, _ = select_matches_by_threshold(matches, threshold_percent=40, minimum_results=5)

    professor_ids = [match.professor_id for match in selected]
    assert professor_ids == [1, 2, 3, 4, 5]
    assert len(professor_ids) == len(set(professor_ids))


def test_missing_threshold_defaults_to_40_percent():
    selected, metadata = select_matches_by_threshold([make_match(1, 0.42), make_match(2, 0.39)], minimum_results=1)

    assert [match.professor_id for match in selected] == [1]
    assert metadata["threshold_percent"] == 40.0


def test_missing_minimum_results_defaults_to_10():
    matches = [make_match(i, 0.9 if i <= 3 else 0.3) for i in range(1, 12)]

    selected, metadata = select_matches_by_threshold(matches, threshold_percent=40)

    assert [match.professor_id for match in selected] == list(range(1, 11))
    assert metadata["minimum_results"] == 10
