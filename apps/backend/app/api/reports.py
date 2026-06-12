from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from apps.backend.app.api.auth import get_current_user
from apps.backend.app.db import get_session
from apps.backend.app.models.auth import User
from apps.backend.app.models.report import Report, utcnow

router = APIRouter(prefix="/reports", tags=["reports"])

VALID_REASONS = {
    "wrong_email", "wrong_title", "wrong_photo", "wrong_bio", "wrong_papers",
    "wrong_tags", "duplicate", "retired_moved", "other",
}

VALID_TARGET_TYPES = {"professor", "publication", "other"}


class CreateReportRequest(BaseModel):
    target_type: str = "professor"
    target_id: Optional[int] = None
    reason: str
    description: str = Field(..., min_length=10, max_length=4000)
    source_url: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def valid_reason(cls, value: str) -> str:
        if value not in VALID_REASONS:
            raise ValueError(f"reason must be one of: {', '.join(sorted(VALID_REASONS))}")
        return value

    @field_validator("target_type")
    @classmethod
    def valid_target_type(cls, value: str) -> str:
        if value not in VALID_TARGET_TYPES:
            raise ValueError(f"target_type must be one of: {', '.join(sorted(VALID_TARGET_TYPES))}")
        return value


class UpdateReportRequest(BaseModel):
    status: str
    admin_notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"new", "resolved", "rejected"}:
            raise ValueError("status must be new, resolved, or rejected")
        return value


def _report_dict(report: Report) -> dict:
    return {
        "id": report.id,
        "reporter_user_id": report.reporter_user_id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason,
        "description": report.description,
        "source_url": report.source_url,
        "status": report.status,
        "admin_notes": report.admin_notes,
        "created_at": report.created_at.isoformat(),
    }


@router.post("")
def create_report(
    payload: CreateReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    report = Report(
        reporter_user_id=current_user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description.strip(),
        source_url=(payload.source_url or "").strip() or None,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return {"status": "submitted", "id": report.id, "message": "Thanks. Our team will review this report."}


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@router.get("/admin", dependencies=[Depends(_require_admin)])
def list_reports(status: Optional[str] = None, limit: int = 100, session: Session = Depends(get_session)):
    stmt = select(Report)
    if status:
        stmt = stmt.where(Report.status == status)
    reports = session.exec(stmt.order_by(Report.created_at.desc()).limit(min(max(limit, 1), 500))).all()
    return {"reports": [_report_dict(r) for r in reports]}


@router.patch("/admin/{report_id}", dependencies=[Depends(_require_admin)])
def update_report(report_id: int, payload: UpdateReportRequest, session: Session = Depends(get_session)):
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = payload.status
    if payload.admin_notes is not None:
        report.admin_notes = payload.admin_notes.strip() or None
    report.updated_at = utcnow()
    session.add(report)
    session.commit()
    session.refresh(report)
    return {"report": _report_dict(report)}
