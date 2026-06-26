from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.routes import require_api_key
from app.services.response_feedback import (
    MAX_REVIEW_LABEL_CHARS,
    MAX_REVIEW_LIST_ITEMS,
    MAX_REVIEW_NOTE_CHARS,
    MAX_REVIEW_QUERY_CHARS,
    MAX_REVIEW_TEXT_CHARS,
    get_response_feedback_store,
)

router = APIRouter()

ResponseFeedbackReasonCode = Literal[
    "wrong_fact",
    "wrong_number",
    "unsupported_claim",
    "weak_evidence",
    "bad_reasoning",
    "incomplete",
    "irrelevant",
    "unclear",
    "poor_structure",
    "other",
]


class ResponseFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    session_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    message_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    parent_message_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    user_label: str | None = Field(default="issue_report", max_length=MAX_REVIEW_LABEL_CHARS)
    reason_code: ResponseFeedbackReasonCode
    note: str | None = Field(default=None, max_length=MAX_REVIEW_NOTE_CHARS)
    query_text: str | None = Field(default=None, max_length=MAX_REVIEW_QUERY_CHARS)
    final_answer_text: str = Field(..., max_length=MAX_REVIEW_TEXT_CHARS)
    ticker: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    company_name: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    route_type: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    model_label: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    confidence_label: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    trust_label: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    sources_present: bool = False
    source_ids: list[str] = Field(default_factory=list, max_length=MAX_REVIEW_LIST_ITEMS)
    source_summary: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_REVIEW_LIST_ITEMS)
    trace_artifact_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    scratchpad_artifact_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    evidence_bundle_id: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    used_financial_truth: bool | None = None
    used_company_memory: bool | None = None
    used_market_memory: bool | None = None
    used_transcript_context: bool | None = None
    response_latency_ms: float | None = None
    extraction_run_ids: list[str] = Field(default_factory=list, max_length=MAX_REVIEW_LIST_ITEMS)
    document_ids: list[str] = Field(default_factory=list, max_length=MAX_REVIEW_LIST_ITEMS)
    provenance_status: dict[str, Any] | None = None
    app_version: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    commit_hash: str | None = Field(default=None, max_length=MAX_REVIEW_LABEL_CHARS)
    verifier_result: dict[str, Any] | None = None


class ResponseFeedbackResponse(BaseModel):
    ok: bool = True
    feedback_id: str
    created_at: str
    storage_path: str


@router.post(
    "/feedback",
    response_model=ResponseFeedbackResponse,
    dependencies=[Depends(require_api_key)],
)
async def cockpit_response_feedback(payload: ResponseFeedbackRequest) -> ResponseFeedbackResponse:
    """Persist non-authoritative response review feedback in a dedicated local store."""

    if not str(payload.final_answer_text or "").strip():
        raise HTTPException(status_code=400, detail="final_answer_text is required")

    store = get_response_feedback_store()
    try:
        result = await asyncio.to_thread(
            store.insert,
            payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ResponseFeedbackResponse(**result)
