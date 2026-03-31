from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.strategy_controller import apply_change, confirm_change, propose_change
from app.services.tenn_chat import _degraded_chat_payload, _json_safe_value, chat_with_tenn


router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    mode: Literal["analysis", "strategy"]
    ticker: str | None = None
    session_id: str | None = None


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
) -> dict[str, Any]:
    try:
        content = chat_with_tenn(
            message,
            ticker=ticker,
            session_id=session_id,
        )
        return {
            "type": "analysis",
            "content": _json_safe_value(content),
        }
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        logger.exception("chat route degraded message=%s error=%s", str(message or "")[:120], detail)
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
            )
        return _strategy_response(payload.message)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
