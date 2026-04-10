from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.chat_quality_scorer import score_turn
from app.services.session_memory import _build_turn_payload, get_relevant_session_context, record_turn
from app.services.strategy_controller import (
    apply_change,
    confirm_change,
    propose_change,
)
from app.services.tenn_chat import (
    _degraded_chat_payload,
    _json_safe_value,
    chat_with_tenn,
)


router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    mode: Literal["analysis", "strategy"]
    ticker: str | None = None
    session_id: str | None = None
    model: str | None = None


def _extract_proposal_id(message: str, prefix: str) -> str:
    text = str(message or "").strip()
    if not text.lower().startswith(prefix):
        raise ValueError(f"Message must start with '{prefix}'")
    proposal_id = text[len(prefix) :].strip()
    if not proposal_id:
        raise ValueError("proposal_id is required")
    return proposal_id


def _strategy_response(message: str) -> dict[str, Any]:
    text = str(message or "").strip()
    lowered = text.lower()
    if lowered.startswith("confirm "):
        proposal = confirm_change(_extract_proposal_id(text, "confirm "))
        return {"type": "confirmation", "content": proposal}
    if lowered.startswith("apply "):
        proposal = apply_change(_extract_proposal_id(text, "apply "))
        return {"type": "confirmation", "content": proposal}
    return {"type": "proposal", "content": propose_change(text)}


def _analysis_response(
    message: str,
    *,
    ticker: str | None,
    session_id: str | None,
    model: str | None = None,
) -> dict[str, Any]:
    try:
        content = chat_with_tenn(
            message,
            ticker=ticker,
            session_id=session_id,
        )

        # Extract the pending turn built inside chat_with_tenn (if session is active).
        # We pop it here so it is never forwarded to the API caller.
        pending_turn: dict[str, Any] | None = content.pop("_pending_turn", None)

        # Issue 1 fix: retrieve the previous query from session memory so that
        # session coherence scoring uses real data instead of always returning 1.0.
        prev_query: str | None = None
        if session_id:
            try:
                prior = get_relevant_session_context(session_id, message, limit=1)
                if prior:
                    prev_query = str(prior[0].get("query") or "").strip() or None
            except Exception as ctx_exc:
                logger.warning("session_context_lookup failed: %s", ctx_exc)

        # Issue 2 + 3 fix: score quality BEFORE recording the turn so that
        # quality_metrics can be persisted with the turn payload.
        quality_metrics: dict[str, Any] | None = None
        try:
            retrieval_hits = content.get("sources", [])
            model_confidence = float(content.get("confidence", 0.85))
            quality_metrics = score_turn(
                query=message,
                session_id=session_id or "unknown",
                retrieval_hits=retrieval_hits,
                model_confidence=model_confidence,
                prev_query=prev_query,
            )
            logger.info(
                "chat_quality_metrics session_id=%s composite=%.3f retrieval=%.3f confidence=%.3f coherence=%.3f",
                session_id or "unknown",
                quality_metrics["composite_metric"],
                quality_metrics["retrieval_precision"],
                quality_metrics["model_confidence"],
                quality_metrics["session_coherence"],
            )
        except Exception as score_exc:
            logger.warning("chat_quality_scorer failed: %s", score_exc)

        # Record the turn now that quality metrics are available.
        if pending_turn is not None:
            try:
                turn_session_id: str = pending_turn["session_id"]
                base_payload: dict[str, Any] = pending_turn["payload"]
                if quality_metrics is not None:
                    # Rebuild payload with quality_metrics included.
                    final_payload = _build_turn_payload(
                        session_id=base_payload["session_id"],
                        query=base_payload["query"],
                        answer=base_payload["answer"],
                        ticker=base_payload.get("ticker"),
                        confidence=base_payload.get("confidence"),
                        sources=base_payload.get("sources"),
                        retrieved_chunk_ids=base_payload.get("retrieved_chunk_ids"),
                        quality_metrics=quality_metrics,
                    )
                else:
                    final_payload = base_payload
                record_turn(turn_session_id, final_payload)
            except Exception as record_exc:
                logger.warning("record_turn failed: %s", record_exc)

        return {
            "type": "analysis",
            "content": _json_safe_value(content),
        }
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        logger.exception(
            "chat route degraded message=%s error=%s", str(message or "")[:120], detail
        )
        return {
            "type": "analysis",
            "content": _degraded_chat_payload(
                "Chat analysis failed before a valid response could be returned.",
                error=detail,
            ),
        }


@router.post("/chat")
def chat(payload: ChatRequest, request: Request) -> dict[str, Any]:
    try:
        if payload.mode == "analysis":
            session_id = str(payload.session_id or "").strip() or (
                str(request.headers.get("X-Session-ID") or "").strip() or None
            )
            return _analysis_response(
                payload.message,
                ticker=payload.ticker,
                session_id=session_id,
                model=payload.model,
            )
        return _strategy_response(payload.message)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
