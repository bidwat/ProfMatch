from datetime import datetime
from typing import Optional

from pydantic import Field

from apps.backend.app.models.base import DocModel, utcnow

USERS = "users"
USER_STATES = "user_states"
AUTH_SESSIONS = "auth_sessions"


class User(DocModel):
    email: str
    password_hash: str
    display_name: str
    role: str = "student"
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_login_at: Optional[datetime] = None


class UserState(DocModel):
    user_id: int
    student_profile: Optional[dict] = None
    last_match_response: Optional[dict] = None
    saved_professor_ids: list[int] = Field(default_factory=list)
    tracker_rows: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AuthSession(DocModel):
    user_id: int
    session_token_hash: str
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    last_seen_at: datetime = Field(default_factory=utcnow)
    revoked_at: Optional[datetime] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
