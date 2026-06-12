from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine, select

from apps.backend.app.main import app
from apps.backend.app.models.auth import AuthSession, User, UserState


def test_delete_account_soft_deletes_user_revokes_sessions_and_clears_cookie(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'delete_account.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    from apps.backend.app import db
    original_engine = db.engine
    db.engine = engine
    try:
        with Session(engine) as session:
            session.exec(delete(AuthSession))
            session.exec(delete(UserState))
            session.exec(delete(User))
            session.commit()

        client = TestClient(app)
        register = client.post("/api/auth/register", json={"email": "delete@example.edu", "password": "strongpass123", "display_name": "Delete Me"})
        assert register.status_code == 201
        assert client.get("/api/auth/me").status_code == 200

        response = client.delete("/api/auth/account")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json={"email": "delete@example.edu", "password": "strongpass123"}).status_code == 401

        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == "delete@example.edu")).first()
            assert user is not None
            assert user.is_active is False
            sessions = session.exec(select(AuthSession).where(AuthSession.user_id == user.id)).all()
            assert sessions
            assert all(s.revoked_at is not None for s in sessions)
    finally:
        db.engine = original_engine
