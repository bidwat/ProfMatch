from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from apps.backend.app.main import app
from apps.backend.app.models.professor import Professor, Publication, RecruitingSignal


def _client_with_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reports.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    from apps.backend.app import db
    original_engine = db.engine
    db.engine = engine
    return TestClient(app), original_engine, engine


def test_report_flow_requires_auth_and_reaches_admin_queue(tmp_path):
    client, original_engine, engine = _client_with_db(tmp_path)
    from apps.backend.app import db
    try:
        payload = {"target_type": "professor", "target_id": 1, "reason": "wrong_email", "description": "The listed email bounces; the faculty page shows a new one."}
        assert client.post("/api/reports", json=payload).status_code == 401

        assert client.post("/api/auth/register", json={"email": "reporter@example.edu", "password": "strongpass123", "display_name": "Reporter"}).status_code == 201
        created = client.post("/api/reports", json=payload)
        assert created.status_code == 200
        report_id = created.json()["id"]

        bad_reason = client.post("/api/reports", json={**payload, "reason": "not_a_reason"})
        assert bad_reason.status_code == 422

        assert client.get("/api/reports/admin").status_code == 403

        client.cookies.clear()
        assert client.post("/api/auth/register", json={"email": "admin-rep@example.edu", "password": "strongpass123", "display_name": "Admin Rep"}).status_code == 201
        with Session(engine) as session:
            from apps.backend.app.models.auth import User
            from sqlmodel import select
            admin = session.exec(select(User).where(User.email == "admin-rep@example.edu")).first()
            admin.role = "admin"
            session.add(admin)
            session.commit()

        listed = client.get("/api/reports/admin")
        assert listed.status_code == 200
        assert listed.json()["reports"][0]["reason"] == "wrong_email"

        resolved = client.patch(f"/api/reports/admin/{report_id}", json={"status": "resolved", "admin_notes": "Email corrected."})
        assert resolved.status_code == 200
        assert resolved.json()["report"]["status"] == "resolved"
    finally:
        db.engine = original_engine


def test_outreach_draft_requires_profile_and_grounds_on_professor(tmp_path, monkeypatch):
    client, original_engine, engine = _client_with_db(tmp_path)
    from apps.backend.app import db
    try:
        with Session(engine) as session:
            professor = Professor(
                name="Eva Example", normalized_name="eva example", university="Test U",
                department="CS", research_text="Robot learning", research_summary="Robot learning research",
                recruiting_signal=RecruitingSignal.unknown, source_confidence=0.9,
            )
            session.add(professor)
            session.commit()
            session.refresh(professor)
            session.add(Publication(professor_id=professor.id, title="Robots That Learn", year=2025, venue="RSS", source="test", match_confidence=0.9))
            session.commit()
            professor_id = professor.id

        assert client.post("/api/outreach-drafts", json={"professor_id": professor_id}).status_code == 401

        assert client.post("/api/auth/register", json={"email": "draft@example.edu", "password": "strongpass123", "display_name": "Drafter"}).status_code == 201

        # Without a research profile the endpoint must refuse.
        no_profile = client.post("/api/outreach-drafts", json={"professor_id": professor_id})
        assert no_profile.status_code == 400

        assert client.patch("/api/auth/state", json={"student_profile": {"research_interests": "robot learning", "target_degree": "PhD"}}).status_code == 200

        from apps.backend.app.api import outreach
        def fake_llm(prompt, is_json=True):
            assert "Eva Example" in prompt and "Robots That Learn" in prompt
            return {"subject": "Prospective PhD student — robot learning", "body": "Dear Professor Example…", "suggested_paper": "Robots That Learn", "personalization_checklist": ["Mention your robotics project"]}
        monkeypatch.setattr("apps.backend.app.services.agentic_onboarding_service._call_llm", fake_llm)

        draft = client.post("/api/outreach-drafts", json={"professor_id": professor_id, "purpose": "phd_inquiry"})
        assert draft.status_code == 200
        body = draft.json()
        assert body["subject"].startswith("Prospective PhD")
        assert "does not send this email" in body["review_reminder"]

        missing = client.post("/api/outreach-drafts", json={"professor_id": 99999})
        assert missing.status_code == 404
    finally:
        db.engine = original_engine
