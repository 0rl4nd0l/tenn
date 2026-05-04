"""Classify cockpit assistant output for Pilot Mode guardrails.

The classifier separates harmless conversational recovery from factual answers.
It is intentionally lightweight: final financial truth enforcement still belongs
to backend evidence and source-contract guards.
"""

from __future__ import annotations

import re

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass


class ResponseClassification(StrEnum):
    CONVERSATIONAL_CLARIFICATION = "conversational_clarification"
    PLANNING_RESPONSE = "planning_response"
    ACTION_PROPOSAL = "action_proposal"
    TOOL_CALL = "tool_call"
    EVIDENCE_BOUND_ANSWER = "evidence_bound_answer"
    UNSUPPORTED_FINANCIAL_CLAIM = "unsupported_financial_claim"
    SYSTEM_FAILURE = "system_failure"


_CONCRETE_VALUE_RE = re.compile(
    r"\$[\d,]+(?:\.\d+)?[MBKmb]?\b|"
    r"\b\d+(?:\.\d+)?\s*%|"
    r"\b\d+(?:\.\d+)?\s*(?:billion|million|bn|mn)\b",
    re.IGNORECASE,
)
_MARKET_EVENT_RE = re.compile(
    r"\b(?:announced|reported|upgraded|downgraded|raised|cut|beat|missed|"
    r"acquired|merged|divested|appointed|resigned|flagged|guided|earnings|"
    r"dividend|buyback|placement|capital\s+raise|takeover)\b",
    re.IGNORECASE,
)
_METRIC_WITH_VALUE_RE = re.compile(
    r"\b(?:revenue|profit|loss|npat|ebit|ebitda|cash\s*flow|net\s+debt|"
    r"margin|capex|dividend|eps|pe|p/e|fcf|free\s+cash\s+flow)\b"
    r".{0,80}?"
    r"(?:\$[\d,]+|\b\d+(?:\.\d+)?\s*(?:%|billion|million|bn|mn)\b)|"
    r"(?:\$[\d,]+|\b\d+(?:\.\d+)?\s*(?:%|billion|million|bn|mn)\b)"
    r".{0,80}?"
    r"\b(?:revenue|profit|loss|npat|ebit|ebitda|cash\s*flow|net\s+debt|"
    r"margin|capex|dividend|eps|pe|p/e|fcf|free\s+cash\s+flow)\b",
    re.IGNORECASE | re.DOTALL,
)
_CLARIFICATION_RE = re.compile(
    r"\b(?:which|what|who|ticker|company|stock|do you mean|did you mean|"
    r"clarify|narrow|specify|one more detail|this company|that company)\b",
    re.IGNORECASE,
)
_PLANNING_RE = re.compile(
    r"\b(?:i can|i could|i would|i'll|i will|we should|we can|we could|"
    r"next(?:\s+we)?\s+(?:check|look|pull|compare|inspect)|"
    r"first(?:\s+we)?\s+(?:check|look|pull|compare|inspect)|"
    r"check next|look up|fetch|pull|inspect|run a|propose|plan|"
    r"before i answer|not enough evidence|cannot verify|can't verify)\b",
    re.IGNORECASE,
)
_SYSTEM_FAILURE_RE = re.compile(
    r"\b(?:i encountered an error|language model|backend|tool execution|"
    r"request failed|timed out|timeout|unavailable|could not complete|"
    r"system failure|service initialization failed)\b",
    re.IGNORECASE,
)


def contains_unsupported_financial_assertion(text: str) -> bool:
    """Return True when text appears to assert a concrete financial fact."""
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    return bool(
        _MARKET_EVENT_RE.search(cleaned)
        or _METRIC_WITH_VALUE_RE.search(cleaned)
        or _CONCRETE_VALUE_RE.search(cleaned)
    )


def classify_agent_output(
    *,
    response_type: str,
    text: str,
    has_current_turn_evidence: bool,
    requires_grounding: bool,
) -> ResponseClassification:
    """Classify a parsed assistant output for orchestration guardrails."""
    normalized_type = str(response_type or "").strip()
    cleaned = str(text or "").strip()

    if normalized_type in {"tool_call", "tool_calls"}:
        return ResponseClassification.TOOL_CALL
    if normalized_type == "action_proposal":
        return ResponseClassification.ACTION_PROPOSAL
    if has_current_turn_evidence:
        return ResponseClassification.EVIDENCE_BOUND_ANSWER

    has_financial_assertion = contains_unsupported_financial_assertion(cleaned)
    if has_financial_assertion:
        return ResponseClassification.UNSUPPORTED_FINANCIAL_CLAIM

    if _SYSTEM_FAILURE_RE.search(cleaned):
        return ResponseClassification.SYSTEM_FAILURE
    if _CLARIFICATION_RE.search(cleaned) and (
        "?" in cleaned or "need" in cleaned.lower() or "mean" in cleaned.lower()
    ):
        return ResponseClassification.CONVERSATIONAL_CLARIFICATION
    if _PLANNING_RE.search(cleaned):
        return ResponseClassification.PLANNING_RESPONSE
    if not requires_grounding:
        return ResponseClassification.EVIDENCE_BOUND_ANSWER
    return ResponseClassification.UNSUPPORTED_FINANCIAL_CLAIM
