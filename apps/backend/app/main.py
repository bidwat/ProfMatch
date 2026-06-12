import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

from apps.backend.app.config import settings
from apps.backend.app.db import engine
from apps.backend.app.api.professors import router as professors_router
from apps.backend.app.api.universities import router as universities_router
from apps.backend.app.api.stats import router as stats_router
from apps.backend.app.api.match import router as match_router
from apps.backend.app.api.auth import router as auth_router
from apps.backend.app.api.admin import router as admin_router
from apps.backend.app.api.scrape_runs import router as scrape_runs_router
from apps.backend.app.api.recommendations import router as recommendations_router
from apps.backend.app.api.student_profiles import router as student_profiles_router
from apps.backend.app.api.reports import router as reports_router
from apps.backend.app.api.outreach import router as outreach_router
from apps.backend.app.api.events import router as events_router
from apps.backend.app.models import auth as auth_models  # noqa: F401 - ensure auth tables are registered
from apps.backend.app.models import scan_job as scan_job_models  # noqa: F401 - ensure durable scan tables are registered
from apps.backend.app.models import report as report_models  # noqa: F401 - ensure report table is registered
from apps.backend.app.models import analytics as analytics_models  # noqa: F401 - ensure analytics table is registered

# --- Structured Logging Setup ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

logger = logging.getLogger("profmatch")
logger.setLevel(settings.log_level)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Professor Match Backend")
    create_db_and_tables()
    yield
    logger.info("Shutting down Professor Match Backend")


app = FastAPI(title="Professor Match Backend", lifespan=lifespan)

# --- CORS Config ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Rate Limiting ---
# The deployment runs a single backend process behind Caddy, so per-process
# buckets are the actual global limit. Revisit with Redis if instances scale.
rate_limits = defaultdict(list)

RATE_LIMIT_EXEMPT_READ_PREFIXES = (
    "/api/auth/me",
    "/api/auth/state",
    "/api/professors",
    "/api/admin/scans/status",
    "/api/admin/agentic/jobs",
    "/api/admin/agentic/job/",
)


def _client_ip(request: Request) -> str:
    # Behind the Caddy reverse proxy every connection comes from localhost;
    # use the first hop in X-Forwarded-For so limits apply per real client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_key(request: Request) -> str:
    client_ip = _client_ip(request)
    path = request.url.path
    if path in {"/api/auth/login", "/api/auth/register"}:
        return f"{client_ip}:auth-write:{path}"
    # Keep local development limits scoped to method + route. A previous shared
    # write bucket made normal flows (match + state save + admin delete) trip
    # unrelated rate limits from the same localhost IP.
    return f"{client_ip}:{request.method}:{path}"


def _rate_limit_for(request: Request) -> int | None:
    if not request.url.path.startswith("/api"):
        return None
    if request.method == "GET" and request.url.path.startswith(RATE_LIMIT_EXEMPT_READ_PREFIXES):
        return None
    if request.url.path in {"/api/auth/login", "/api/auth/register"}:
        return max(20, settings.rate_limit_per_minute // 5)
    if request.method in {"POST", "PATCH", "DELETE"}:
        return max(120, settings.rate_limit_per_minute)
    return settings.rate_limit_per_minute


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    """Tag every request with an id and emit a structured access log line."""
    request_id = request.headers.get("x-request-id", "").strip() or uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    if request.url.path.startswith("/api") or request.url.path == "/health":
        logger.info(json.dumps({
            "event": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": _client_ip(request),
        }))
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    limit = _rate_limit_for(request)
    if limit is not None:
        key = _rate_limit_key(request)
        now = time.time()
        rate_limits[key] = [t for t in rate_limits[key] if now - t < 60]
        if len(rate_limits[key]) >= limit:
            logger.warning(f"Rate limit exceeded for key: {key}")
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limit_exceeded", "message": "Too many requests. Please wait a moment, then try again."}},
                headers={"Retry-After": "30"},
            )
        rate_limits[key].append(now)

    response = await call_next(request)
    return response

# --- Structured JSON Errors ---

def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception: {exc.detail} (status {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail), "request_id": _request_id(request)}},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = jsonable_encoder(exc.errors())
    logger.error(f"Validation Error: {errors}")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Invalid request parameters", "details": errors}},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred. Please try again later.", "request_id": _request_id(request)}},
    )


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(professors_router, prefix="/api")
app.include_router(universities_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(scrape_runs_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
app.include_router(student_profiles_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(outreach_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(admin_router, prefix="/api")