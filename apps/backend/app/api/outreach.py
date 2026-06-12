from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from apps.backend.app.api.auth import get_current_user, get_or_create_user_state
from apps.backend.app.db import get_session
from apps.backend.app.models.auth import User
from apps.backend.app.models.professor import Professor, Publication

router = APIRouter(prefix="/outreach-drafts", tags=["outreach"])

PURPOSES = {
    "phd_inquiry": "PhD inquiry",
    "masters_research_inquiry": "Master's research inquiry",
    "undergraduate_research_inquiry": "Undergraduate research inquiry",
    "research_assistantship": "Research assistantship",
    "general_introduction": "General prospective student introduction",
    "follow_up": "Follow-up email",
}

REVIEW_REMINDER = (
    "ProfMatch does not send this email. Review the professor's website, verify any "
    "contact instructions, and personalize this draft before sending. Do not send "
    "identical emails to many professors."
)


class OutreachDraftRequest(BaseModel):
    professor_id: int
    purpose: str = Field(default="phd_inquiry")
    extra_context: Optional[str] = Field(default=None, max_length=2000)


@router.post("")
def generate_outreach_draft(
    payload: OutreachDraftRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if payload.purpose not in PURPOSES:
        raise HTTPException(status_code=422, detail=f"purpose must be one of: {', '.join(sorted(PURPOSES))}")

    professor = session.get(Professor, payload.professor_id)
    if not professor:
        raise HTTPException(status_code=404, detail="Professor not found")

    publications = session.exec(
        select(Publication).where(Publication.professor_id == professor.id).order_by(Publication.year.desc()).limit(5)
    ).all()

    state = get_or_create_user_state(session, current_user)
    profile = state.student_profile or {}
    interests = str(profile.get("research_interests") or "").strip()
    if not interests:
        raise HTTPException(status_code=400, detail="Create your research profile (interests) before drafting outreach.")

    publication_context = "\n".join(
        f"- {p.title} ({p.year}), {p.venue}: {(p.abstract or '')[:400]}" for p in publications
    ) or "- No reliably matched publications; ground the draft in the research summary only."

    prompt = f"""
Write a professor outreach email draft for a prospective student. Return STRICT JSON:
{{"subject": str, "body": str, "suggested_paper": str | null, "personalization_checklist": [str]}}

Rules:
- Ground every claim in the evidence below; never invent papers, funding, or recruiting status.
- Reference at most one specific publication if a relevant one exists.
- Professional, concise (under 180 words for the body), specific to this professor.
- Do not promise admission or imply the professor is recruiting unless evidence says so.

Purpose: {PURPOSES[payload.purpose]}
Student name: {current_user.display_name}
Student interests: {interests[:1200]}
Student background: {str(profile.get('background') or '')[:1200]}
Target degree: {profile.get('target_degree') or 'PhD'}
Extra context from student: {(payload.extra_context or '')[:1000]}

Professor: {professor.name}, {professor.title or 'Faculty'}, {professor.department}, {professor.university}
Research summary: {(professor.research_summary or professor.research_text or '')[:2000]}
Recent publications:
{publication_context[:4000]}
"""
    from apps.backend.app.services.agentic_onboarding_service import _call_llm

    try:
        draft = _call_llm(prompt, is_json=True)
    except Exception:
        raise HTTPException(status_code=503, detail="Draft generation is unavailable right now. Try again in a moment.")

    if not isinstance(draft, dict) or not draft.get("subject") or not draft.get("body"):
        raise HTTPException(status_code=503, detail="Draft generation returned an unusable result. Try again.")

    return {
        "professor_id": professor.id,
        "professor_name": professor.name,
        "purpose": payload.purpose,
        "subject": str(draft.get("subject")),
        "body": str(draft.get("body")),
        "suggested_paper": draft.get("suggested_paper"),
        "personalization_checklist": [str(item) for item in draft.get("personalization_checklist") or []],
        "review_reminder": REVIEW_REMINDER,
    }
