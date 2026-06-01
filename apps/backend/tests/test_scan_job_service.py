from sqlmodel import Session, SQLModel, create_engine, select

from apps.backend.app.models.auth import User
from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.models.scan_job import ScanJob, ScanLog, ScanResult, ScanTask
from apps.backend.app.services.scan_job_service import ScanJobService


def make_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_create_job_tasks_and_claim_once():
    with make_session() as session:
        service = ScanJobService(session)
        job = service.create_scan_job(items=[{"university": "U1", "department": "CS", "faculty_url": "https://example.edu/cs"}], settings={})

        assert job.total_tasks == 1
        assert job.queued_tasks == 1
        task = service.claim_next_scan_task("worker-1", lease_seconds=60)
        assert task is not None
        assert task.status == "running"
        assert task.locked_by == "worker-1"
        assert service.claim_next_scan_task("worker-2", lease_seconds=60) is None


def test_task_success_recalculates_job_progress():
    with make_session() as session:
        service = ScanJobService(session)
        job = service.create_scan_job(items=[{"university": "U1", "department": "CS", "faculty_url": "https://example.edu/cs"}], settings={})
        task = service.claim_next_scan_task("worker-1", lease_seconds=60)

        service.mark_task_succeeded(task.id, {"candidate_count": 2})
        refreshed = service.get_scan_job(job.id)

        assert refreshed.status == "completed"
        assert refreshed.progress_percent == 100.0
        assert refreshed.succeeded_tasks == 1


def test_failed_task_retries_then_fails():
    with make_session() as session:
        service = ScanJobService(session)
        job = service.create_scan_job(items=[{"university": "U1", "department": "CS", "faculty_url": "https://example.edu/cs"}], settings={"max_attempts": 1})
        task = service.claim_next_scan_task("worker-1", lease_seconds=60)

        service.mark_task_failed(task.id, "boom", retryable=True)
        failed = service.get_scan_task(task.id)
        refreshed = service.get_scan_job(job.id)

        assert failed.status == "failed"
        assert refreshed.status == "completed_with_errors"
        assert refreshed.failed_tasks == 1


def test_save_results_and_idempotent_import_duplicate():
    with make_session() as session:
        service = ScanJobService(session)
        job = service.create_scan_job(items=[{"university": "U1", "department": "CS", "faculty_url": "https://example.edu/cs"}], settings={})
        task = service.claim_next_scan_task("worker-1", lease_seconds=60)
        results = service.save_scan_results(job.id, task.id, [{"name": "Ada Lovelace", "university": "U1", "department": "CS", "email": "ada@example.edu", "publications": [{"title": "Computing"}]}])

        service.approve_scan_result(results[0].id)
        imported = service.import_scan_result(results[0].id)
        imported_again = service.import_scan_result(results[0].id)

        assert imported.import_status == "imported"
        assert imported.imported_professor_id is not None
        assert imported_again.imported_professor_id == imported.imported_professor_id
        assert len(session.exec(select(Professor)).all()) == 1
        assert len(session.exec(select(Publication)).all()) == 1
