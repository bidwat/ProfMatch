from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    reporter_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    target_type: str = Field(index=True)  # professor, publication, other
    target_id: Optional[int] = Field(default=None, index=True)
    reason: str  # wrong_email, wrong_title, wrong_bio, wrong_papers, wrong_tags, duplicate, retired_moved, other
    description: str
    source_url: Optional[str] = None
    status: str = Field(default="new", index=True)  # new, resolved, rejected
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
