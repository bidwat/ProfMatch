from fastapi.testclient import TestClient

from apps.backend.app.db import MemoryDatabase
from apps.backend.app.main import app
from apps.backend.app.models.auth import AUTH_SESSIONS, USERS


def test_delete_account_soft_deletes_user_revokes_sessions_and_clears_cookie(memory_db: MemoryDatabase):
    client = TestClient(app)
    register = client.post("/api/auth/register", json={"email": "delete@example.edu", "password": "strongpass123", "display_name": "Delete Me"})
    assert register.status_code == 201
    assert client.get("/api/auth/me").status_code == 200

    response = client.delete("/api/auth/account")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "delete@example.edu", "password": "strongpass123"}).status_code == 401

    user = memory_db.collection(USERS).find_one(email="delete@example.edu")
    assert user is not None
    assert user["is_active"] is False
    sessions = memory_db.collection(AUTH_SESSIONS).find(user_id=user["id"])
    assert sessions
    assert all(s["revoked_at"] is not None for s in sessions)
