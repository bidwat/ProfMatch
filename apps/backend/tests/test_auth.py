from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine

from apps.backend.app.main import app
from apps.backend.app.models.auth import AuthSession, User, UserState

TEST_DATABASE_URL = "sqlite:///./test_auth.sqlite"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)


def test_register_login_me_logout_flow():
    SQLModel.metadata.create_all(test_engine)
    from apps.backend.app import db

    original_engine = db.engine
    db.engine = test_engine
    try:
        with Session(test_engine) as session:
            session.exec(delete(AuthSession))
            session.exec(delete(UserState))
            session.exec(delete(User))
            session.commit()

        client = TestClient(app)
        register = client.post(
            "/api/auth/register",
            json={"email": "Student@Example.edu", "password": "strongpass123", "display_name": "Student User"},
        )
        assert register.status_code == 201
        assert register.json()["user"]["email"] == "student@example.edu"
        assert "profmatch_session" in client.cookies

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["display_name"] == "Student User"

        empty_state = client.get("/api/auth/state")
        assert empty_state.status_code == 200
        assert empty_state.json()["saved_professor_ids"] == []

        patched_state = client.patch(
            "/api/auth/state",
            json={
                "student_profile": {"research_interests": "robotics", "target_degree": "PhD"},
                "last_match_response": {"matches": [{"professor_id": 42}]},
                "saved_professor_ids": [42],
                "tracker_rows": [{"id": 1, "professor": "Ada", "status": "Contacted"}],
            },
        )
        assert patched_state.status_code == 200
        assert patched_state.json()["student_profile"]["research_interests"] == "robotics"
        assert patched_state.json()["saved_professor_ids"] == [42]
        assert client.get("/api/auth/state").json()["tracker_rows"][0]["status"] == "Contacted"

        duplicate = client.post(
            "/api/auth/register",
            json={"email": "student@example.edu", "password": "strongpass123", "display_name": "Other"},
        )
        assert duplicate.status_code == 409

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 200
        assert client.get("/api/auth/me").status_code == 401

        bad_login = client.post("/api/auth/login", json={"email": "student@example.edu", "password": "wrong"})
        assert bad_login.status_code == 401

        login = client.post("/api/auth/login", json={"email": "student@example.edu", "password": "strongpass123"})
        assert login.status_code == 200
        assert client.get("/api/auth/me").status_code == 200
    finally:
        db.engine = original_engine
        import os

        if os.path.exists("./test_auth.sqlite"):
            os.remove("./test_auth.sqlite")


def test_register_requires_strong_enough_password():
    SQLModel.metadata.create_all(test_engine)
    from apps.backend.app import db

    original_engine = db.engine
    db.engine = test_engine
    try:
        client = TestClient(app)
        response = client.post(
            "/api/auth/register",
            json={"email": "new@example.edu", "password": "short", "display_name": "New User"},
        )
        assert response.status_code == 422
    finally:
        db.engine = original_engine
