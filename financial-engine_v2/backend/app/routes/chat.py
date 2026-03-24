from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.strategy_controller import apply_change, confirm_change, propose_change
from app.services.tenn_chat import chat_with_tenn


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    mode: Literal["analysis", "strategy"]
    ticker: str | None = None


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


@router.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    try:
        if payload.mode == "analysis":
            return {"type": "analysis", "content": chat_with_tenn(payload.message, ticker=payload.ticker)}
        return _strategy_response(payload.message)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
