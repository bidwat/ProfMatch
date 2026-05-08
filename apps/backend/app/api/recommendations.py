import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from apps.backend.app.api.auth import get_current_user
from apps.backend.app.models.auth import User
from apps.backend.app.services.recommendation_service import RecommendationService, REQUESTS_PATH

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

class RecommendationRequest(BaseModel):
    university: str = Field(..., min_length=2, max_length=160)
    department: str = Field(..., min_length=2, max_length=160)
    faculty_page_url: str = Field(..., min_length=8, max_length=2000)

    @field_validator("university", "department")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Field is required")
        return cleaned

    @field_validator("faculty_page_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        url = value.strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Enter a valid http or https URL")
        hostname = parsed.hostname or ""
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or hostname.endswith(".local"):
            raise ValueError("Faculty page URL must be publicly reachable")
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError("Faculty page URL must be publicly reachable")
        except ValueError as exc:
            if "publicly reachable" in str(exc):
                raise
        return url


@router.post("")
def create_recommendation(payload: RecommendationRequest, current_user: User = Depends(get_current_user)):
    try:
        record = RecommendationService(REQUESTS_PATH).create(current_user, payload)
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save recommendation: {exc}")
    return {"status": "submitted", "id": record["id"], "message": "Thanks — your recommendation was submitted."}
