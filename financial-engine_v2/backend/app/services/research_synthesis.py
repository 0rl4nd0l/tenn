"""Research synthesis service — LLM-based synthesis of gathered research sources.

Receives gathered source data from the cockpit's DeepResearchRunner and
synthesizes a structured research brief via the backend LLM. This keeps
all LLM calls inside the backend layer (service role invariant).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.llamacpp_runtime import (
    build_llm_headers,
    resolve_llm_runtime_config,
    verify_llm_models,
)

logger = logging.getLogger(__name__)

_RESEARCH_SYSTEM_PROMPT = """\
You are an ASX equity research analyst. You have been given data from multiple
sources about a company. Synthesize this into a concise research brief.

Output ONLY valid JSON with these fields:
{
  "summary": "2-3 sentence overview of the company's current situation",
  "key_metrics": {"revenue": "...", "ebit": "...", "cash_flow": "...", "net_debt": "..."},
  "recent_developments": ["development 1", "development 2"],
  "sentiment": "bullish|neutral|bearish",
  "confidence": 0.0-1.0,
  "risks": ["risk 1", "risk 2"],
  "catalysts": ["catalyst 1", "catalyst 2"],
  "data_gaps": ["what data is missing or uncertain"],
  "strategy_evaluation": [{"criterion": "...", "verdict": "met|not_met|insufficient_data", "evidence": "..."}]
}

If the DATA includes a "strategy_criteria" section with user-defined investment
criteria, evaluate each criterion against the evidence and populate
"strategy_evaluation". If no criteria are provided, omit or return an empty list.

Be concise. Cite specific numbers from the data. Flag low-confidence claims.
"""

_MAX_DATA_CHARS = 8000
_DEFAULT_TIMEOUT = 120.0


def synthesize_research(
    ticker: str,
    gathered_sources: dict[str, Any],
    *,
    focus: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Synthesize gathered research sources into a structured brief.

    Args:
        ticker: ASX ticker symbol.
        gathered_sources: Dict of source category → data (financials, price, web, etc.).
        focus: Optional focus area (earnings, risk, valuation, catalysts).
        timeout: LLM call timeout in seconds.

    Returns:
        Structured brief dict with summary, key_metrics, sentiment, risks, etc.
    """
    if not gathered_sources:
        return _empty_brief(ticker, reason="No data gathered")

    # Build user message with gathered data.
    focus_instruction = f"\nFocus your analysis on: {focus}" if focus else ""
    data_text = json.dumps(gathered_sources, default=str, ensure_ascii=False)
    if len(data_text) > _MAX_DATA_CHARS:
        data_text = data_text[:_MAX_DATA_CHARS] + "\n... (truncated)"

    user_msg = f"Research {ticker} on the ASX.{focus_instruction}\n\nDATA:\n{data_text}"

    messages = [
        {"role": "system", "content": _RESEARCH_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw_text = _call_llm(messages, timeout=timeout)
        return _parse_synthesis(raw_text)
    except Exception as exc:
        logger.warning("research_synthesis: LLM call failed for %s: %s", ticker, exc)
        return _empty_brief(ticker, reason=f"LLM synthesis failed: {str(exc)[:200]}")


# ------------------------------------------------------------------
# LLM call — uses the same llama.cpp /v1/chat/completions as extraction
# ------------------------------------------------------------------


def _call_llm(messages: list[dict[str, str]], *, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """Call llama.cpp chat completions with explicit messages list."""
    base_url, model = resolve_llm_runtime_config(
        base_url=settings.llamacpp_url,
        model="",
    )
    headers = build_llm_headers()

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        models_payload = verify_llm_models(base_url, headers=headers, timeout=timeout, client=client)
        available = models_payload.get("data", [])
        resolved_model = available[0]["id"] if available else "default"

        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }

        response = client.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices", [])
    if not choices or not isinstance(choices[0], dict):
        raise RuntimeError(f"Bad llama.cpp response: no choices in {data}")

    message = choices[0].get("message", {})
    return str(message.get("content", ""))


# ------------------------------------------------------------------
# Response parsing — moved from cockpit deep_research.py
# ------------------------------------------------------------------


def _parse_synthesis(raw: str) -> dict[str, Any]:
    """Parse LLM JSON output with fallback to plain text."""
    text = raw.strip()

    # Strip markdown fences if present.
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: treat raw text as summary.
    return {
        "summary": text[:500],
        "key_metrics": {},
        "recent_developments": [],
        "sentiment": "neutral",
        "confidence": 0.3,
        "risks": [],
        "catalysts": [],
        "data_gaps": ["LLM returned non-JSON response"],
    }


def _empty_brief(ticker: str, *, reason: str = "Unknown") -> dict[str, Any]:
    return {
        "summary": f"{reason} for {ticker}.",
        "key_metrics": {},
        "recent_developments": [],
        "sentiment": "neutral",
        "confidence": 0.0,
        "risks": [reason],
        "catalysts": [],
        "data_gaps": [reason],
    }
