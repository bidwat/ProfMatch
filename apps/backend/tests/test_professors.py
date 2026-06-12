import pytest
from fastapi.testclient import TestClient

from apps.backend.app.db import MemoryDatabase
from apps.backend.app.main import app
from apps.backend.app.models.professor import PROFESSORS, PUBLICATIONS, Professor, Publication, RecruitingSignal


@pytest.fixture()
def test_client():
    return TestClient(app)


@pytest.fixture()
def sample_data(memory_db: MemoryDatabase):
    professors = memory_db.collection(PROFESSORS)
    publications = memory_db.collection(PUBLICATIONS)
    prof1 = Professor(
        name="John Doe",
        normalized_name="john doe",
        title="Assistant Professor",
        university="Test University",
        department="Computer Science",
        research_text="AI and Machine Learning",
        research_summary="Research in AI",
        faculty_profile_url="https://example.edu/john",
        recruiting_signal=RecruitingSignal.positive,
        source_confidence=0.9,
        extra={"image_url": "https://example.edu/john.jpg", "image_source": "university_profile", "tags": ["Machine Learning", "AI"]},
    )
    prof2 = Professor(
        name="Jane Smith",
        normalized_name="jane smith",
        title="Professor",
        university="Another University",
        department="Engineering",
        research_text="Robotics",
        research_summary="Robotics research",
        recruiting_signal=RecruitingSignal.unknown,
        source_confidence=0.8,
    )
    prof1.id = professors.add(prof1.to_doc())
    prof2.id = professors.add(prof2.to_doc())

    publications.add(Publication(
        professor_id=prof1.id,
        title="AI Paper",
        year=2023,
        venue="AI Journal",
        source="Scholar",
        match_confidence=0.95,
    ).to_doc())
    publications.add(Publication(
        professor_id=prof1.id,
        title="ML Paper",
        year=2022,
        venue="ML Conf",
        source="Scholar",
        match_confidence=0.9,
    ).to_doc())

    return {"prof1": prof1, "prof2": prof2}


def test_health(test_client: TestClient):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_professors_empty(test_client: TestClient):
    response = test_client.get("/api/professors")
    assert response.status_code == 200
    data = response.json()
    assert data["professors"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 20


def test_list_professors_with_data(test_client: TestClient, sample_data):
    response = test_client.get("/api/professors")
    assert response.status_code == 200
    data = response.json()
    assert len(data["professors"]) == 2
    assert data["total"] == 2
    assert "id" in data["professors"][0]
    assert "name" in data["professors"][0]
    john = next(p for p in data["professors"] if p["name"] == "John Doe")
    assert john["photo_url"] == "https://example.edu/john.jpg"
    assert john["photo_confidence"] == 0.75


def test_list_professors_filter_q(test_client: TestClient, sample_data):
    response = test_client.get("/api/professors?q=AI")
    assert response.status_code == 200
    data = response.json()
    assert len(data["professors"]) == 1
    assert data["professors"][0]["name"] == "John Doe"


def test_list_professors_filter_university(test_client: TestClient, sample_data):
    response = test_client.get("/api/professors?university=Test University")
    assert response.status_code == 200
    data = response.json()
    assert len(data["professors"]) == 1
    assert data["professors"][0]["university"] == "Test University"


def test_list_professors_filter_title(test_client: TestClient, sample_data):
    response = test_client.get("/api/professors?title=Assistant Professor")
    assert response.status_code == 200
    data = response.json()
    assert len(data["professors"]) == 1
    assert data["professors"][0]["title"] == "Assistant Professor"
    response = test_client.get("/api/professors?page=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["professors"]) == 1
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["limit"] == 1
    assert data["next_cursor"] is not None


def test_list_professors_server_side_facets_filters_sort_and_cursor(test_client: TestClient, sample_data):
    facets = test_client.get("/api/professors/facets")
    assert facets.status_code == 200
    assert "Machine Learning" in facets.json()["tags"]
    assert "Test University" in facets.json()["universities"]

    filtered = test_client.get("/api/professors?tag=Machine Learning&recruiting_signal=positive&sort=name-desc&limit=1")
    assert filtered.status_code == 200
    filtered_data = filtered.json()
    assert filtered_data["total"] == 1
    assert filtered_data["professors"][0]["name"] == "John Doe"

    first = test_client.get("/api/professors?sort=name-asc&limit=1").json()
    second = test_client.get(f"/api/professors?sort=name-asc&limit=1&cursor={first['next_cursor']}").json()
    assert first["professors"][0]["name"] != second["professors"][0]["name"]


def test_get_professor_existing(test_client: TestClient, sample_data):
    prof_id = sample_data["prof1"].id
    response = test_client.get(f"/api/professors/{prof_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["professor"]["name"] == "John Doe"
    assert data["professor"]["photo_url"] == "https://example.edu/john.jpg"
    assert data["professor"]["photo_source_url"] is not None
    assert len(data["publications"]) == 2
    assert data["publications"][0]["year"] >= data["publications"][1]["year"]


def test_match_rejects_whitespace_only_research_interests(test_client: TestClient):
    response = test_client.post("/api/match", json={"research_interests": "   ", "target_degree": "PhD"})
    assert response.status_code == 422


def test_get_professor_not_found(test_client: TestClient):
    response = test_client.get("/api/professors/999")
    assert response.status_code == 404
    assert "Professor not found" in response.json()["error"]["message"]


def test_get_professor_invalid_id(test_client: TestClient):
    response = test_client.get("/api/professors/0")
    assert response.status_code == 422
    assert "Invalid professor ID" in response.json()["error"]["message"]


def test_get_professor_negative_id(test_client: TestClient):
    response = test_client.get("/api/professors/-1")
    assert response.status_code == 422
