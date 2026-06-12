from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from apps.backend.app.main import app


def _client_with_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'events.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    from apps.backend.app import db
    original_engine = db.engine
    db.engine = engine
    return TestClient(app), original_engine, engine


def test_event_tracking_and_admin_metrics(tmp_path):
    client, original_engine, engine = _client_with_db(tmp_path)
    from apps.backend.app import db
    try:
        # Anonymous events are accepted; unknown names and oversized values are controlled.
        assert client.post("/api/events", json={"name": "search_performed", "properties": {"filters_count": 2, "query_length": 14}}).status_code == 200
        assert client.post("/api/events", json={"name": "profile_opened", "properties": {"professor_id": 7, "padding": "x" * 500}}).status_code == 200
        assert client.post("/api/events", json={"name": "made_up_event"}).status_code == 422

        from apps.backend.app.models.analytics import AnalyticsEvent
        with Session(engine) as session:
            stored = session.exec(select(AnalyticsEvent)).all()
            assert len(stored) == 2
            padded = next(e for e in stored if e.name == "profile_opened")
            assert len(padded.properties["padding"]) <= 120

        assert client.get("/api/admin/metrics").status_code == 401

        assert client.post("/api/auth/register", json={"email": "metrics-admin@example.edu", "password": "strongpass123", "display_name": "Metrics Admin"}).status_code == 201
        with Session(engine) as session:
            from apps.backend.app.models.auth import User
            admin = session.exec(select(User).where(User.email == "metrics-admin@example.edu")).first()
            admin.role = "admin"
            session.add(admin)
            session.commit()

        metrics = client.get("/api/admin/metrics")
        assert metrics.status_code == 200
        body = metrics.json()
        assert body["total_events"] == 2
        assert {e["name"] for e in body["events"]} == {"search_performed", "profile_opened"}
    finally:
        db.engine = original_engine
