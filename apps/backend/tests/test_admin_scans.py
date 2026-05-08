import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from apps.backend.app.api.admin import require_admin
from apps.backend.app.api.auth import get_current_user
from apps.backend.app.db import get_session
from apps.backend.app.main import app
from apps.backend.app.models.auth import User
from apps.backend.app.models.professor import Professor, Publication, RecruitingSignal
from apps.backend.app.services import admin_scan_service


def _admin_user():
    return User(id=1, email="admin@example.edu", display_name="Admin", password_hash="x", role="admin")


def _student_user():
    return User(id=2, email="student@example.edu", display_name="Student", password_hash="x", role="student")


def test_admin_scan_artifacts_are_listed(tmp_path, monkeypatch):
    qa_dir = tmp_path / "data" / "qa" / "scraper_runs"
    qa_dir.mkdir(parents=True)
    validation = qa_dir / "2026-05-01_stanford-university_validation.json"
    validation.write_text(
        """
        {
          "run": {
            "university": "Stanford University",
            "department": "Computer Science",
            "adapter_name": "stanford",
            "started_at": "2026-05-01T00:00:00+00:00",
            "completed_at": "2026-05-01T00:01:00+00:00",
            "status": "success"
          },
          "status": "ready_for_review",
          "summary": {"professors": 2, "publications": 0, "duplicates": 1, "errors": 1, "warnings": 1, "total_issues": 2},
          "issues": [
            {"severity":"error","code":"missing_required_field","field_name":"faculty_profile_url","record_type":"professor","record_index":0,"message":"Missing required professor field: faculty_profile_url"},
            {"severity":"warning","code":"missing_research_provenance","field_name":"research_text","record_type":"professor","record_index":1,"message":"research_text exists but field_sources.research_text is missing"}
          ],
          "duplicates": [{"left_index":0,"right_index":1,"confidence":0.91,"reason":"same profile URL"}],
          "artifact_paths": {"raw": "/tmp/raw.html", "professors": "/tmp/professors.jsonl", "publications": "/tmp/publications.jsonl"},
          "db_import_allowed": false
        }
        """
    )
    (qa_dir / "2026-05-01_stanford-university_scan_manifest.json").write_text('{"import_policy":"No SQLite import"}')
    (qa_dir / "2026-05-01_stanford-university_openrouter_audit.json").write_text('{"status":"disabled","model":null}')
    monkeypatch.setattr(admin_scan_service, "QA_SCAN_DIR", qa_dir)

    app.dependency_overrides[require_admin] = _admin_user
    client = TestClient(app)
    response = client.get("/api/admin/scans")
    assert response.status_code == 200
    scans = response.json()["scans"]
    assert len(scans) == 1
    assert scans[0]["id"] == "2026-05-01_stanford-university"
    assert scans[0]["university"] == "Stanford University"
    assert scans[0]["professors"] == 2
    assert scans[0]["duplicates"] == 1
    assert scans[0]["db_import_allowed"] is False
    assert scans[0]["issue_breakdown"]["missing_required_fields"]["professor.faculty_profile_url"] == 1
    assert scans[0]["issues_preview"][0]["code"] == "missing_required_field"
    assert scans[0]["duplicate_candidates"][0]["confidence"] == 0.91

    detail = client.get("/api/admin/scans/2026-05-01_stanford-university")
    assert detail.status_code == 200
    assert detail.json()["validation"]["status"] == "ready_for_review"
    assert detail.json()["openrouter_audit"]["status"] == "disabled"
    assert detail.json()["issues_preview"][1]["code"] == "missing_research_provenance"
    app.dependency_overrides.clear()


def test_admin_scan_detail_404s_for_missing_scan(tmp_path, monkeypatch):
    qa_dir = tmp_path / "empty"
    qa_dir.mkdir()
    monkeypatch.setattr(admin_scan_service, "QA_SCAN_DIR", qa_dir)
    app.dependency_overrides[require_admin] = _admin_user
    client = TestClient(app)
    response = client.get("/api/admin/scans/nope")
    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_admin_scan_import(tmp_path, monkeypatch):
    qa_dir = tmp_path / "data" / "qa" / "scraper_runs"
    qa_dir.mkdir(parents=True)
    
    import json
    
    # Fake processed files
    prof_path = tmp_path / "prof.jsonl"
    pub_path = tmp_path / "pub.jsonl"
    
    prof_path.write_text(json.dumps({
        "name": "Jane Import",
        "normalized_name": "jane import",
        "university": "Test U",
        "department": "CS",
        "faculty_profile_url": "http://test.u/jane",
        "source_confidence": 0.9,
    }) + "\n")
    
    pub_path.write_text(json.dumps({
        "title": "A Great Paper",
        "year": 2026,
        "venue": "Test Conf",
        "url": "http://test.u/paper",
        "source": "DBLP",
        "source_author_id": "123",
        "match_confidence": 0.8,
        "extra": {
            "professor_normalized_name": "jane import",
            "professor_university": "Test U"
        }
    }) + "\n")
    
    validation = qa_dir / "2026-05-01_test-import_validation.json"
    validation.write_text(json.dumps({
        "run": {"university": "Test U", "status": "success"},
        "status": "ready_for_review",
        "summary": {"professors": 1, "publications": 1},
        "db_import_allowed": True,
        "artifact_paths": {
            "professors": str(prof_path),
            "publications": str(pub_path)
        }
    }))
    (qa_dir / "2026-05-01_test-import_scan_manifest.json").write_text("{}")
    (qa_dir / "2026-05-01_test-import_openrouter_audit.json").write_text("{}")
    
    monkeypatch.setattr(admin_scan_service, "QA_SCAN_DIR", qa_dir)
    
    app.dependency_overrides[require_admin] = _admin_user
    client = TestClient(app)
    response = client.post("/api/admin/scans/2026-05-01_test-import/import")
    assert response.status_code == 200
    res = response.json()
    assert res["professors_inserted"] + res["professors_updated"] == 1
    assert res["publications_inserted"] + res["publications_updated"] == 1
    assert res["errors"] == []
    
    app.dependency_overrides.clear()


def test_admin_scans_require_admin_role():
    with pytest.raises(HTTPException) as exc:
        require_admin(_student_user())
    assert exc.value.status_code == 403


def test_admin_indexed_departments_and_delete_are_admin_only(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin_indexed.sqlite'}", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        professor = Professor(
            name="Indexed Prof",
            normalized_name="indexed prof",
            university="Indexed U",
            department="CS",
            recruiting_signal=RecruitingSignal.unknown,
            source_confidence=0.8,
        )
        session.add(professor)
        session.commit()
        session.refresh(professor)
        session.add(Publication(professor_id=professor.id, title="Paper", year=2026, venue="Conf", source="DBLP", match_confidence=0.8))
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = _student_user
        assert client.get("/api/admin/indexed-departments").status_code == 403

        app.dependency_overrides[get_current_user] = _admin_user
        listed = client.get("/api/admin/indexed-departments")
        assert listed.status_code == 200
        assert listed.json()["groups"][0]["professor_count"] == 1
        assert listed.json()["groups"][0]["publication_count"] == 1

        blocked_delete = client.request("DELETE", "/api/admin/indexed-departments", json={"university": "Indexed U", "department": "CS", "confirm": False})
        assert blocked_delete.status_code == 400
        deleted = client.request("DELETE", "/api/admin/indexed-departments", json={"university": "Indexed U", "department": "CS", "confirm": True})
        assert deleted.status_code == 200
        assert deleted.json()["professors_deleted"] == 1
    finally:
        app.dependency_overrides.clear()
