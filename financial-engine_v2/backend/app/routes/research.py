"""Research endpoints — synthesis of gathered research sources."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes import require_api_key
from app.services.research_synthesis import synthesize_research

router = APIRouter()


class SynthesizeRequest(BaseModel):
    ticker: str
    focus: str | None = None
    gathered_sources: dict[str, Any]


class SynthesisBrief(BaseModel):
    summary: str
    key_metrics: dict[str, Any] = {}
    recent_developments: list[str] = []
    sentiment: str = "neutral"
    confidence: float = 0.0
    risks: list[str] = []
    catalysts: list[str] = []
    data_gaps: list[str] = []


@router.post(
    "/synthesize",
    response_model=SynthesisBrief,
    dependencies=[Depends(require_api_key)],
)
def synthesize(payload: SynthesizeRequest) -> dict[str, Any]:
    """Synthesize gathered research sources into a structured brief.

    Called by the cockpit's DeepResearchRunner. All LLM inference
    happens server-side (service role invariant).
    """
    try:
        return synthesize_research(
            ticker=payload.ticker,
            gathered_sources=payload.gathered_sources,
            focus=payload.focus,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc
