from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    display_name: str
    role: str = Field(default="student")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_login_at: Optional[datetime] = None


class UserState(SQLModel, table=True):
    __tablename__ = "user_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    student_profile: Optional[dict] = Field(default=None, sa_type=JSON)
    last_match_response: Optional[dict] = Field(default=None, sa_type=JSON)
    saved_professor_ids: list[int] = Field(default_factory=list, sa_type=JSON)
    tracker_rows: list[dict] = Field(default_factory=list, sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_token_hash: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at: datetime
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    revoked_at: Optional[datetime] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
