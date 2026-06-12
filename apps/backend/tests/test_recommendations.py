from fastapi.testclient import TestClient

from apps.backend.app.db import MemoryDatabase
from apps.backend.app.main import app
from apps.backend.app.models.auth import USERS


def test_recommendation_requires_auth_and_writes_jsonl(tmp_path, monkeypatch):
    client = TestClient(app)
    from apps.backend.app.api import recommendations
    monkeypatch.setattr(recommendations, "REQUESTS_PATH", tmp_path / "recommendation_requests.jsonl")

    unauth = client.post("/api/recommendations", json={"university": "Example", "department": "CS", "faculty_page_url": "https://example.edu/cs/faculty"})
    assert unauth.status_code == 401

    register = client.post("/api/auth/register", json={"email": "rec@example.edu", "password": "strongpass123", "display_name": "Rec User"})
    assert register.status_code == 201

    response = client.post("/api/recommendations", json={"university": " Example University ", "department": " Computer Science ", "faculty_page_url": "https://example.edu/cs/faculty"})
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    contents = (tmp_path / "recommendation_requests.jsonl").read_text()
    assert "Example University" in contents
    assert "rec@example.edu" in contents


def test_recommendation_rejects_private_or_invalid_urls(tmp_path):
    client = TestClient(app)
    assert client.post("/api/auth/register", json={"email": "badurl@example.edu", "password": "strongpass123", "display_name": "Bad URL"}).status_code == 201
    for url in ["ftp://example.edu/faculty", "http://localhost/faculty", "http://127.0.0.1/faculty", "http://10.0.0.2/faculty"]:
        response = client.post("/api/recommendations", json={"university": "Example", "department": "CS", "faculty_page_url": url})
        assert response.status_code == 422


def test_admin_can_list_recommendation_requests(tmp_path, monkeypatch, memory_db: MemoryDatabase):
    client = TestClient(app)
    from apps.backend.app.api import recommendations
    from apps.backend.app.services import recommendation_service
    requests_path = tmp_path / "recommendation_requests.jsonl"
    monkeypatch.setattr(recommendations, "REQUESTS_PATH", requests_path)
    monkeypatch.setattr(recommendation_service, "REQUESTS_PATH", requests_path)

    assert client.post("/api/auth/register", json={"email": "student-rec@example.edu", "password": "strongpass123", "display_name": "Student Rec"}).status_code == 201
    assert client.post("/api/recommendations", json={"university": "Requested University", "department": "Computer Science", "faculty_page_url": "https://example.edu/cs/faculty"}).status_code == 200
    assert client.get("/api/admin/recommendations").status_code == 403

    client.cookies.clear()
    assert client.post("/api/auth/register", json={"email": "admin-rec@example.edu", "password": "strongpass123", "display_name": "Admin Rec"}).status_code == 201
    admin = memory_db.collection(USERS).find_one(email="admin-rec@example.edu")
    memory_db.collection(USERS).update(admin["id"], {"role": "admin"})

    response = client.get("/api/admin/recommendations")
    assert response.status_code == 200
    rows = response.json()["requests"]
    assert rows[0]["university"] == "Requested University"
