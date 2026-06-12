import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from apps.backend.app.models.auth import AuthSession, User

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
SESSION_DAYS = 14


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = stored_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.exec(select(User).where(User.email == normalize_email(email))).first()

    def register(self, email: str, password: str, display_name: str) -> User:
        normalized = normalize_email(email)
        if self.get_user_by_email(normalized):
            raise ValueError("email_already_registered")
        user = User(
            email=normalized,
            password_hash=hash_password(password),
            display_name=display_name.strip(),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_session(self, user: User, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> tuple[str, AuthSession]:
        token = secrets.token_urlsafe(32)
        session = AuthSession(
            user_id=user.id,
            session_token_hash=hash_session_token(token),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=SESSION_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return token, session

    def get_user_for_token(self, token: str) -> Optional[User]:
        if not token:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        session = self.db.exec(
            select(AuthSession).where(AuthSession.session_token_hash == hash_session_token(token))
        ).first()
        if not session or session.revoked_at is not None or session.expires_at <= now:
            return None
        user = self.db.get(User, session.user_id)
        if not user or not user.is_active:
            return None
        session.last_seen_at = now
        self.db.add(session)
        self.db.commit()
        return user

    def revoke_token(self, token: str) -> None:
        session = self.db.exec(
            select(AuthSession).where(AuthSession.session_token_hash == hash_session_token(token))
        ).first()
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.db.add(session)
            self.db.commit()

    def purge_deactivated_accounts(self, older_than_days: int = 30) -> int:
        """Permanently delete accounts deactivated more than N days ago.

        Implements the deletion policy (spec §26.4): account deletion
        deactivates immediately; personal data is removed permanently after
        the 30-day recovery window. updated_at records the deactivation time.
        """
        from apps.backend.app.models.auth import UserState

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=older_than_days)
        users = self.db.exec(
            select(User).where(User.is_active == False, User.updated_at <= cutoff)  # noqa: E712
        ).all()
        for user in users:
            for auth_session in self.db.exec(select(AuthSession).where(AuthSession.user_id == user.id)).all():
                self.db.delete(auth_session)
            state = self.db.exec(select(UserState).where(UserState.user_id == user.id)).first()
            if state:
                self.db.delete(state)
            self.db.delete(user)
        if users:
            self.db.commit()
        return len(users)
