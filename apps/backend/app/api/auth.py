from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from apps.backend.app.db import get_session
from apps.backend.app.models.auth import AuthSession, User, UserState
from apps.backend.app.services.auth_service import AuthService, SESSION_DAYS

AUTH_COOKIE = "profmatch_session"
COOKIE_MAX_AGE = SESSION_DAYS * 24 * 60 * 60

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthUser(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    user: AuthUser


class UserStateResponse(BaseModel):
    student_profile: Optional[dict] = None
    last_match_response: Optional[dict] = None
    saved_professor_ids: list[int] = Field(default_factory=list)
    tracker_rows: list[dict] = Field(default_factory=list)


class UserStatePatch(BaseModel):
    student_profile: Optional[dict] = None
    last_match_response: Optional[dict] = None
    saved_professor_ids: Optional[list[int]] = None
    tracker_rows: Optional[list[dict]] = None


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=256)
    display_name: str = Field(..., min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def valid_emailish(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Enter a valid email address")
        return email

    @field_validator("display_name")
    @classmethod
    def valid_display_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Display name is required")
        return name


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


def user_to_response(user: User) -> AuthResponse:
    return AuthResponse(user=AuthUser.model_validate(user, from_attributes=True))


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        AUTH_COOKIE,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE, path="/")


def get_or_create_user_state(session: Session, user: User) -> UserState:
    state = session.exec(select(UserState).where(UserState.user_id == user.id)).first()
    if state:
        return state
    state = UserState(user_id=user.id)
    session.add(state)
    session.commit()
    session.refresh(state)
    return state


def state_to_response(state: UserState) -> UserStateResponse:
    return UserStateResponse(
        student_profile=state.student_profile,
        last_match_response=state.last_match_response,
        saved_professor_ids=state.saved_professor_ids or [],
        tracker_rows=state.tracker_rows or [],
    )


def get_current_user(
    profmatch_session: Optional[str] = Cookie(default=None),
    session: Session = Depends(get_session),
) -> User:
    user = AuthService(session).get_user_for_token(profmatch_session or "")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    service = AuthService(session)
    try:
        user = service.register(payload.email, payload.password, payload.display_name)
    except ValueError as exc:
        if str(exc) == "email_already_registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        raise
    token, _ = service.create_session(
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, token)
    return user_to_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    service = AuthService(session)
    user = service.authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token, _ = service.create_session(
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, token)
    return user_to_response(user)


@router.post("/logout")
def logout(response: Response, profmatch_session: Optional[str] = Cookie(default=None), session: Session = Depends(get_session)):
    if profmatch_session:
        AuthService(session).revoke_token(profmatch_session)
    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=AuthResponse)
def me(current_user: User = Depends(get_current_user)):
    return user_to_response(current_user)


@router.delete("/account")
def delete_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_user.is_active = False
    current_user.updated_at = now
    auth_sessions = session.exec(select(AuthSession).where(AuthSession.user_id == current_user.id)).all()
    for auth_session in auth_sessions:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = now
            session.add(auth_session)
    session.add(current_user)
    session.commit()
    clear_session_cookie(response)
    return {"status": "deleted"}


@router.get("/state", response_model=UserStateResponse)
def get_state(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return state_to_response(get_or_create_user_state(session, current_user))


@router.patch("/state", response_model=UserStateResponse)
def patch_state(payload: UserStatePatch, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    state = get_or_create_user_state(session, current_user)
    updates = payload.model_dump(exclude_unset=True)
    if "student_profile" in updates:
        state.student_profile = payload.student_profile
    if "last_match_response" in updates:
        state.last_match_response = payload.last_match_response
    if payload.saved_professor_ids is not None:
        state.saved_professor_ids = payload.saved_professor_ids
    if payload.tracker_rows is not None:
        state.tracker_rows = payload.tracker_rows
    state.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(state)
    session.commit()
    session.refresh(state)
    return state_to_response(state)
