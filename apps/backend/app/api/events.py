from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from apps.backend.app.api.auth import get_current_user
from apps.backend.app.db import get_session
from apps.backend.app.models.analytics import AnalyticsEvent, utcnow
from apps.backend.app.models.auth import User
from apps.backend.app.services.auth_service import AuthService

router = APIRouter(tags=["analytics"])

# Core product events from doc.md §7.3. Unknown names are rejected so the
# event stream stays queryable.
ALLOWED_EVENTS = {
    "search_performed",
    "filter_applied",
    "profile_opened",
    "source_link_clicked",
    "professor_saved",
    "match_requested",
    "match_result_opened",
    "board_card_moved",
    "outreach_draft_generated",
    "report_submitted",
    "department_requested",
    "signup_started",
    "paid_feature_modal_shown",
}

# Properties are size-limited and never include raw query text, document
# content, or emails (privacy rule from design.md §14).
MAX_PROPERTIES = 12
MAX_VALUE_LENGTH = 120


class TrackEventRequest(BaseModel):
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
def track_event(
    payload: TrackEventRequest,
    profmatch_session: Optional[str] = Cookie(default=None),
    session: Session = Depends(get_session),
):
    if payload.name not in ALLOWED_EVENTS:
        raise HTTPException(status_code=422, detail="Unknown event name")
    cleaned: dict[str, Any] = {}
    for key, value in list(payload.properties.items())[:MAX_PROPERTIES]:
        if isinstance(value, (int, float, bool)) or value is None:
            cleaned[str(key)[:60]] = value
        else:
            cleaned[str(key)[:60]] = str(value)[:MAX_VALUE_LENGTH]
    user = AuthService(session).get_user_for_token(profmatch_session or "") if profmatch_session else None
    event = AnalyticsEvent(user_id=user.id if user else None, name=payload.name, properties=cleaned)
    session.add(event)
    session.commit()
    return {"status": "ok"}


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@router.get("/admin/metrics", dependencies=[Depends(_require_admin)])
def admin_metrics(days: int = 30, session: Session = Depends(get_session)):
    since = utcnow() - timedelta(days=min(max(days, 1), 365))
    rows = session.exec(
        select(AnalyticsEvent.name, func.count(AnalyticsEvent.id))
        .where(AnalyticsEvent.created_at >= since)
        .group_by(AnalyticsEvent.name)
        .order_by(func.count(AnalyticsEvent.id).desc())
    ).all()
    total = session.exec(select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.created_at >= since)).one()
    return {
        "days": days,
        "total_events": int(total or 0),
        "events": [{"name": name, "count": int(count or 0)} for name, count in rows],
    }
