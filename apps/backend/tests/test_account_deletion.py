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


def test_purge_removes_accounts_past_thirty_day_window(tmp_path):
    from datetime import datetime, timedelta, timezone
    from apps.backend.app.services.auth_service import AuthService

    engine = create_engine(f"sqlite:///{tmp_path / 'purge.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        service = AuthService(session)
        old = service.register("old-deleted@example.edu", "strongpass123", "Old Deleted")
        recent = service.register("recent-deleted@example.edu", "strongpass123", "Recent Deleted")
        active = service.register("active@example.edu", "strongpass123", "Still Active")
        service.create_session(old)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        old.is_active = False
        old.updated_at = now - timedelta(days=31)
        recent.is_active = False
        recent.updated_at = now - timedelta(days=5)
        session.add(old)
        session.add(recent)
        session.commit()

        purged = service.purge_deactivated_accounts(older_than_days=30)
        assert purged == 1
        remaining = {u.email for u in session.exec(select(User)).all()}
        assert remaining == {"recent-deleted@example.edu", "active@example.edu"}
        assert session.exec(select(AuthSession)).all() == []
        assert active.is_active is True
