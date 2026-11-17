from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.routes import require_api_key
from app.services.claim_verification import verify_claims_against_evidence

logger = logging.getLogger(__name__)

router = APIRouter()


class ClaimVerificationSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str | None = None
    url: str | None = None
    score: float | None = None
    snippet: str | None = None
    published_at: str | None = None
    document_id: str | None = None
    source_id: str | None = None
    doc_type: str | None = None
    path: str | None = None
    kind: str | None = None


class ClaimVerificationRequest(BaseModel):
    session_id: str | None = None
    message_id: str | None = None
    parent_prompt: str | None = None
    assistant_text: str
    ticker: str | None = None
    route_type: str | None = None
    visible_sources: list[ClaimVerificationSource] = Field(default_factory=list)
    transcript_context: list[dict[str, Any]] = Field(default_factory=list)


class ClaimVerificationVerdict(BaseModel):
    claim_id: str
    claim_text: str
    verdict: Literal[
        "supported",
        "contradicted",
        "insufficient_evidence",
        "not_checkable",
    ]
    short_reason: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    uncheckable_reason: str | None = None
    confidence: Literal["low", "medium", "high"] = "low"


class ClaimVerificationResponse(BaseModel):
    ok: bool = True
    session_id: str | None = None
    message_id: str | None = None
    checked_at: str
    evidence_scope: str
    evidence_count: int
    verdicts: list[ClaimVerificationVerdict] = Field(default_factory=list)


def _current_turn_evidence(session_id: str | None, assistant_text: str) -> list[dict[str, Any]]:
    """Read recent in-process chat diagnostics without creating a CockpitService."""
    try:
        from app.services.cockpit_service import CockpitService
    except Exception:
        return []

    service = getattr(CockpitService, "_instance", None)
    if service is None:
        return []

    try:
        resolve_thread_id = getattr(service, "_resolve_thread_id", None)
        thread_id = (
            resolve_thread_id(session_id)
            if callable(resolve_thread_id)
            else (str(session_id or "").strip() or "global-main")
        )
        resolver = getattr(service, "_resolve_turn_diagnostics", None)
        if not callable(resolver):
            return []
        matched = resolver(thread_id, {"content": assistant_text})
    except Exception as exc:
        logger.debug("Claim verification diagnostics lookup failed: %s", exc)
        return []

    if not isinstance(matched, dict):
        return []
    evidence = matched.get("evidence")
    return evidence if isinstance(evidence, list) else []


@router.post(
    "/claims/verify",
    response_model=ClaimVerificationResponse,
    dependencies=[Depends(require_api_key)],
)
async def cockpit_verify_claims(payload: ClaimVerificationRequest) -> ClaimVerificationResponse:
    assistant_text = str(payload.assistant_text or "").strip()
    if not assistant_text:
        raise HTTPException(status_code=400, detail="assistant_text is required")

    visible_sources = [item.model_dump(exclude_none=True) for item in payload.visible_sources]
    turn_evidence = _current_turn_evidence(payload.session_id, assistant_text)
    result = verify_claims_against_evidence(
        answer_text=assistant_text,
        visible_sources=visible_sources,
        turn_evidence=turn_evidence,
    )
    evidence_scope = "visible_sources"
    if turn_evidence:
        evidence_scope = "backend_turn_and_visible_sources"

    return ClaimVerificationResponse(
        session_id=payload.session_id,
        message_id=payload.message_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        evidence_scope=evidence_scope,
        evidence_count=int(result["evidence_count"]),
        verdicts=result["verdicts"],
    )
