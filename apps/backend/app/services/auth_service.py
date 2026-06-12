import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from apps.backend.app.db import Database
from apps.backend.app.models.auth import AUTH_SESSIONS, USERS, AuthSession, User

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


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(self, db: Database):
        self.db = db
        self.users = db.collection(USERS)
        self.sessions = db.collection(AUTH_SESSIONS)

    def get_user_by_email(self, email: str) -> Optional[User]:
        doc = self.users.find_one(email=normalize_email(email))
        return User.from_doc(doc) if doc else None

    def register(self, email: str, password: str, display_name: str) -> User:
        normalized = normalize_email(email)
        if self.get_user_by_email(normalized):
            raise ValueError("email_already_registered")
        user = User(
            email=normalized,
            password_hash=hash_password(password),
            display_name=display_name.strip(),
        )
        user.id = self.users.add(user.to_doc())
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        now = _now()
        user.last_login_at = now
        user.updated_at = now
        self.users.update(user.id, {"last_login_at": now, "updated_at": now})
        return user

    def create_session(self, user: User, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> tuple[str, AuthSession]:
        token = secrets.token_urlsafe(32)
        session = AuthSession(
            user_id=user.id,
            session_token_hash=hash_session_token(token),
            expires_at=_now() + timedelta(days=SESSION_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        session.id = self.sessions.add(session.to_doc())
        return token, session

    def get_user_for_token(self, token: str) -> Optional[User]:
        if not token:
            return None
        now = _now()
        doc = self.sessions.find_one(session_token_hash=hash_session_token(token))
        if not doc:
            return None
        session = AuthSession.from_doc(doc)
        if session.revoked_at is not None or session.expires_at <= now:
            return None
        user_doc = self.users.get(session.user_id)
        if not user_doc:
            return None
        user = User.from_doc(user_doc)
        if not user.is_active:
            return None
        self.sessions.update(session.id, {"last_seen_at": now})
        return user

    def revoke_token(self, token: str) -> None:
        doc = self.sessions.find_one(session_token_hash=hash_session_token(token))
        if doc and doc.get("revoked_at") is None:
            self.sessions.update(doc["id"], {"revoked_at": _now()})

    def revoke_user_sessions(self, user_id: int) -> None:
        now = _now()
        for doc in self.sessions.find(user_id=user_id):
            if doc.get("revoked_at") is None:
                self.sessions.update(doc["id"], {"revoked_at": now})

    def deactivate_user(self, user: User) -> None:
        now = _now()
        self.users.update(user.id, {"is_active": False, "updated_at": now})
        self.revoke_user_sessions(user.id)
