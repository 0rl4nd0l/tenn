"""Narrow continuity helpers for Cockpit chat turns.

This module handles meta-conversation and pronoun carry-over using only the
current session's persisted chat text and recent turn diagnostics. It does not
query market data, write memory, or execute actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cockpit.core.action_preview import normalize_action_preview
from shared.ticker_inference import (
    COMMON_TICKER_STOPWORDS,
    detect_tickers,
    is_valid_ticker_token,
)


class ContinuityTurnKind(str, Enum):
    PREVIOUS_TOOL_TRACE_QUESTION = "previous_tool_trace_question"
    CORRECTION_TURN = "correction_turn"
    THESIS_SAVE = "thesis_save"
    REFERENT_COMPARE = "referent_compare"


@dataclass
class ContinuityResponse:
    text: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    action_preview: dict[str, Any] | None = None
    mode: str = "continuity"
    routing_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompareResolution:
    matched: bool
    rewritten_message: str | None = None
    resolved_tickers: list[str] = field(default_factory=list)
    clarification_text: str | None = None


_FALSE_TICKER_WORDS = frozenset(
    {
        "ACTION",
        "ACTIONS",
        "DATA",
        "NOTE",
        "NOTES",
        "SOURCE",
        "SOURCES",
    }
)
_CONTINUITY_STOPWORDS = COMMON_TICKER_STOPWORDS | _FALSE_TICKER_WORDS

_PREVIOUS_TOOL_TRACE_RE = re.compile(
    r"\bwhy\b.{0,80}\b(?:didn'?t|did\s+not|doesn'?t|fail(?:ed)?|"
    r"return(?:ed)?|work(?:ed)?|no\s+rows?|nothing|error)\b"
    r".{0,80}\b(?:it|that|this|your|previous|last|prior|tool|tools|run|search|"
    r"screener|trace|compare)\b|"
    r"\bwhy\b.{0,80}\b(?:it|that|this|your|previous|last|prior|tool|tools|run|"
    r"search|screener|trace|compare)\b.{0,80}\b(?:didn'?t|did\s+not|doesn'?t|"
    r"fail(?:ed)?|return(?:ed)?|work(?:ed)?|no\s+rows?|nothing|error)\b|"
    r"\b(?:what\s+happened|why)\b.{0,120}\b(?:tool|tools|run|search|screener|"
    r"trace|compare\s+run)\b",
    re.IGNORECASE,
)
_CORRECTION_RE = re.compile(
    r"^\s*(?:no|nah|actually|but)\b.{0,120}\b(?:you|u|tenn|that)\b"
    r".{0,120}\b(?:did|used|ran|called|searched|do|were)\b",
    re.IGNORECASE,
)
_THESIS_SAVE_RE = re.compile(
    r"\b(?:save|store|record|capture|keep)\b.{0,120}\b"
    r"(?:thesis(?:\s+note)?|thesis\s+memory|note)\b|"
    r"\bthesis\s+note\b",
    re.IGNORECASE,
)
_REFERENT_COMPARE_RE = re.compile(
    r"\bcompare\b.{0,80}\b(?:them|those|these|it|that)\b|"
    r"\b(?:it|that|them|those|these)\b.{0,80}\b(?:vs\.?|versus|against|to)\b",
    re.IGNORECASE,
)
_SINGULAR_REFERENT_RE = re.compile(r"\b(?:it|that)\b", re.IGNORECASE)
_PLURAL_REFERENT_RE = re.compile(r"\b(?:them|those|these)\b", re.IGNORECASE)


def classify_continuity_turn(message: str) -> ContinuityTurnKind | None:
    """Classify only the meta/continuity cases this helper owns."""
    text = str(message or "").strip()
    if not text:
        return None
    if _CORRECTION_RE.search(text):
        return ContinuityTurnKind.CORRECTION_TURN
    if _THESIS_SAVE_RE.search(text):
        return ContinuityTurnKind.THESIS_SAVE
    if _PREVIOUS_TOOL_TRACE_RE.search(text):
        return ContinuityTurnKind.PREVIOUS_TOOL_TRACE_QUESTION
    if _REFERENT_COMPARE_RE.search(text):
        return ContinuityTurnKind.REFERENT_COMPARE
    return None


def build_previous_tool_trace_response(
    *,
    message: str,
    latest_turn: dict[str, Any] | None,
    correction: bool = False,
) -> ContinuityResponse:
    """Answer a question/correction about the previous turn's actual tools."""
    calls = _tool_calls_from_turn(latest_turn or {})
    turn_kind = (
        ContinuityTurnKind.CORRECTION_TURN
        if correction
        else ContinuityTurnKind.PREVIOUS_TOOL_TRACE_QUESTION
    )
    if not calls:
        prefix = (
            "You're right to challenge that."
            if correction
            else "I checked the session state."
        )
        return ContinuityResponse(
            text=(
                f"{prefix} I do not have a saved tool trace for the previous assistant "
                "turn in this session, so I can't verify which tools ran."
            ),
            routing_metadata={
                "continuity_turn": turn_kind.value,
                "tool_trace_available": False,
            },
        )

    tool_names = _unique_ordered(str(call.get("tool") or "") for call in calls)
    summaries = [_summarize_tool_call(call) for call in calls]
    no_result_summaries = [
        summary for summary in summaries if summary and _is_no_result_summary(summary)
    ]
    fallback_summaries = [
        summary
        for summary in summaries
        if summary and summary not in no_result_summaries and "failed" not in summary.lower()
    ]

    lines: list[str] = []
    if correction:
        lines.append("You're right. I re-checked the saved prior turn trace: it did use tools.")
    else:
        lines.append("I re-checked the saved prior turn trace. The prior turn did use tools.")
    if tool_names:
        lines.append(f"Tools called: {', '.join(tool_names)}.")
    if no_result_summaries:
        lines.append("The no-result part was:")
        lines.extend(f"- {summary}" for summary in no_result_summaries)
    if fallback_summaries:
        lines.append("Other evidence/tools still ran:")
        lines.extend(f"- {summary}" for summary in fallback_summaries)
    if no_result_summaries:
        lines.append(
            "So this was a tool no-result for that part of the run, not proof that "
            "the whole analysis failed or that no tools were used."
        )

    return ContinuityResponse(
        text="\n".join(lines),
        evidence=_evidence_from_turn(latest_turn or {}),
        routing_metadata={
            "continuity_turn": turn_kind.value,
            "tool_trace_available": True,
            "referenced_tool_names": tool_names,
            "original_message": message,
        },
    )


def resolve_compare_referents(
    *,
    message: str,
    latest_turn: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None,
) -> CompareResolution:
    """Resolve compare pronouns to the latest clear ticker set."""
    if classify_continuity_turn(message) != ContinuityTurnKind.REFERENT_COMPARE:
        return CompareResolution(matched=False)

    current_tickers = _extract_tickers_from_text(message)
    prior_tickers = _extract_recent_tickers(
        latest_turn=latest_turn,
        recent_messages=recent_messages,
    )
    prior_without_current = [ticker for ticker in prior_tickers if ticker not in current_tickers]
    resolved: list[str] = []

    if current_tickers and _SINGULAR_REFERENT_RE.search(message):
        if len(prior_without_current) == 1:
            resolved = [prior_without_current[0], *current_tickers]
        else:
            return CompareResolution(
                matched=True,
                clarification_text=(
                    "Which prior company should I compare to "
                    f"{', '.join(current_tickers)}?"
                ),
            )
    elif current_tickers:
        resolved = _unique_nonempty([*prior_tickers, *current_tickers])
    elif _PLURAL_REFERENT_RE.search(message):
        if 2 <= len(prior_tickers) <= 8:
            resolved = prior_tickers
        elif len(prior_tickers) > 8:
            return CompareResolution(
                matched=True,
                clarification_text=(
                    "I found more than eight recently discussed tickers. Which ones should I compare?"
                ),
            )
        else:
            return CompareResolution(
                matched=True,
                clarification_text="Which companies should I compare?",
            )
    elif _SINGULAR_REFERENT_RE.search(message):
        if len(prior_tickers) == 1:
            resolved = prior_tickers
        else:
            return CompareResolution(
                matched=True,
                clarification_text="Which company does that refer to?",
            )

    resolved = _unique_nonempty(resolved)
    if len(resolved) < 2:
        return CompareResolution(
            matched=True,
            clarification_text="Which companies should I compare?",
        )

    ticker_text = ", ".join(resolved)
    rewritten = (
        f"The pronoun in the user's request resolves to these ASX tickers: {ticker_text}. "
        f"Compare {ticker_text}. Original request: {message}"
    )
    return CompareResolution(
        matched=True,
        rewritten_message=rewritten,
        resolved_tickers=resolved,
    )


def build_thesis_save_response(
    *,
    message: str,
    latest_turn: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None,
) -> ContinuityResponse | None:
    """Build a confirmation-gated thesis-note action from the prior answer."""
    if classify_continuity_turn(message) != ContinuityTurnKind.THESIS_SAVE:
        return None

    explicit_tickers = _extract_tickers_from_text(message)
    prior_tickers = _extract_recent_tickers(
        latest_turn=latest_turn,
        recent_messages=recent_messages,
    )
    ticker_candidates = explicit_tickers or prior_tickers
    if len(ticker_candidates) != 1:
        return ContinuityResponse(
            text="Which ticker should I attach that thesis note to?",
            routing_metadata={
                "continuity_turn": ContinuityTurnKind.THESIS_SAVE.value,
                "requires_clarification": True,
            },
        )

    statement = _latest_assistant_text(
        latest_turn=latest_turn,
        recent_messages=recent_messages,
    )
    if not statement:
        return ContinuityResponse(
            text="I do not have a previous assistant answer in this session to save as a thesis note.",
            routing_metadata={
                "continuity_turn": ContinuityTurnKind.THESIS_SAVE.value,
                "requires_clarification": True,
            },
        )

    ticker = ticker_candidates[0]
    thesis = _compact_thesis_statement(statement)
    args = {
        "ticker": ticker,
        "thesis": thesis,
        "signal": "HOLD",
        "run_risk_gate": False,
    }
    preview = normalize_action_preview(
        {
            "tool": "create_thesis",
            "action_id": "create_thesis",
            "action_label": f"Save thesis note for {ticker}",
            "arguments": args,
            "explanation": f"Save the previous answer as a thesis note for {ticker}.",
            "requires_confirmation": True,
            "is_mutating": True,
            "timeout_seconds": 60,
        }
    )
    return ContinuityResponse(
        text=f"I can save the previous answer as a thesis note for {ticker}. Use /confirm to execute.",
        action_preview=preview,
        mode="action",
        routing_metadata={
            "continuity_turn": ContinuityTurnKind.THESIS_SAVE.value,
            "memory_write_confirmation_required": True,
            "resolved_ticker": ticker,
        },
    )


def _tool_calls_from_turn(turn: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = _evidence_from_turn(turn)
    calls: list[dict[str, Any]] = []
    for item in evidence:
        tool = str(item.get("tool") or "").strip()
        if not tool:
            continue
        calls.append(
            {
                "tool": tool,
                "arguments": item.get("arguments")
                if isinstance(item.get("arguments"), dict)
                else {},
                "result": item.get("result") if isinstance(item.get("result"), dict) else {},
            }
        )

    traces = [item for item in turn.get("tool_traces") or [] if isinstance(item, dict)]
    if not calls:
        for trace in traces:
            tool = str(trace.get("tool") or "").strip()
            if tool:
                calls.append(
                    {
                        "tool": tool,
                        "arguments": {},
                        "result": {
                            "ok": bool(trace.get("ok", True)),
                            "error": trace.get("error"),
                            "hint": trace.get("hint"),
                        },
                    }
                )
    return calls


def _evidence_from_turn(turn: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in turn.get("evidence") or [] if isinstance(item, dict)]


def _summarize_tool_call(call: dict[str, Any]) -> str:
    tool = str(call.get("tool") or "tool").strip()
    args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
    result = call.get("result") if isinstance(call.get("result"), dict) else {}
    ticker = str(result.get("ticker") or args.get("ticker") or "").strip().upper()
    if result.get("ok") is False or result.get("error"):
        error = str(result.get("error") or "tool returned ok=false").strip()
        target = f" for {ticker}" if ticker else ""
        return f"{tool}{target} failed: {error}"

    if tool == "tv_screener":
        market = str(result.get("market") or args.get("market") or "market").strip()
        rows = result.get("results") if isinstance(result.get("results"), list) else []
        if not rows:
            return f"TradingView screener returned no rows for {market}."
        return f"TradingView screener returned {len(rows)} row(s) for {market}."

    if tool == "screen_tickers":
        rows = _first_list(result, "results", "items", "candidates", "tickers")
        if not rows:
            return "screen_tickers returned no candidates."
        return f"screen_tickers returned {len(rows)} candidate(s)."

    if tool in {"query_ticker_data", "gather_local_context", "get_company_dump"}:
        bits = _row_count_bits(
            result,
            ("docs", "financials", "announcements", "announcement_context", "doc_snippets"),
        )
        target = f" for {ticker}" if ticker else ""
        return f"{tool}{target} returned " + (", ".join(bits) if bits else "context payload.")

    if tool == "get_price":
        price = result.get("price") if isinstance(result.get("price"), dict) else {}
        history = (
            price.get("recent_history")
            if isinstance(price.get("recent_history"), list)
            else []
        )
        current = price.get("current") if isinstance(price.get("current"), dict) else {}
        target = ticker or str(price.get("symbol") or args.get("ticker") or "").strip().upper()
        if history or current:
            detail = f"{len(history)} history row(s)" if history else "current price fields"
            return f"get_price for {target or 'ticker'} returned {detail}."
        return f"get_price for {target or 'ticker'} returned no price observations."

    rows = _first_list(result, "results", "hits", "documents", "financials", "items")
    if rows:
        return f"{tool} returned {len(rows)} row(s)."
    if any(key in result for key in ("results", "hits", "documents", "financials", "items")):
        return f"{tool} returned no rows."
    return f"{tool} completed."


def _is_no_result_summary(summary: str) -> bool:
    return bool(
        re.search(r"\breturned no (?:rows|candidates|price observations)\b", summary, re.I)
    )


def _row_count_bits(result: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    bits: list[str] = []
    for key in keys:
        value = result.get(key)
        if isinstance(value, list):
            bits.append(f"{len(value)} {key}")
    return bits


def _first_list(result: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = result.get(key)
        if isinstance(value, list):
            return value
    return []


def _extract_recent_tickers(
    *,
    latest_turn: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None,
) -> list[str]:
    found: list[str] = []
    turn = latest_turn or {}
    request = turn.get("request") if isinstance(turn.get("request"), dict) else {}
    for value in (
        turn.get("ticker"),
        request.get("ticker"),
        request.get("message"),
        turn.get("response_text"),
    ):
        found.extend(_extract_tickers_from_any(value))

    for item in _evidence_from_turn(turn):
        args = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        for payload in (args, result):
            for key in ("ticker", "tickers", "symbol", "symbols"):
                found.extend(_extract_tickers_from_any(payload.get(key)))
            for row_key in ("results", "hits", "items", "candidates", "financials"):
                rows = payload.get(row_key)
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    for key in ("ticker", "symbol", "code", "name"):
                        found.extend(_extract_tickers_from_any(row.get(key)))

    for msg in reversed(recent_messages or []):
        if msg.get("role") not in {"assistant", "user"}:
            continue
        found.extend(_extract_tickers_from_any(msg.get("content")))
        if found:
            break
    return _unique_nonempty(found)


def _extract_tickers_from_text(text: str) -> list[str]:
    return _extract_tickers_from_any(text)


def _extract_tickers_from_any(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        found: list[str] = []
        for item in value:
            found.extend(_extract_tickers_from_any(item))
        return _unique_nonempty(found)
    text = str(value or "")
    tickers: list[str] = []
    for raw in re.split(r"[^A-Za-z0-9.:$]+", text):
        token = raw.strip()
        if not token:
            continue
        if "." in token or ":" in token or token.startswith("$"):
            tickers.extend(detect_tickers(token, stopwords=_CONTINUITY_STOPWORDS))
            continue
        upper = token.upper()
        if is_valid_ticker_token(upper, stopwords=_CONTINUITY_STOPWORDS) and (
            token.isupper() or token.isdigit() or any(char.isdigit() for char in token)
        ):
            tickers.append(upper)
    tickers.extend(detect_tickers(text, stopwords=_CONTINUITY_STOPWORDS))
    return _unique_nonempty(tickers)


def _latest_assistant_text(
    *,
    latest_turn: dict[str, Any] | None,
    recent_messages: list[dict[str, Any]] | None,
) -> str:
    response_text = str((latest_turn or {}).get("response_text") or "").strip()
    if response_text:
        return response_text
    for msg in reversed(recent_messages or []):
        if msg.get("role") == "assistant":
            text = str(msg.get("content") or "").strip()
            if text:
                return text
    return ""


def _compact_thesis_statement(text: str, *, limit: int = 1200) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    cleaned = re.sub(
        r"\s*Use /confirm to execute\.?\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _unique_nonempty(values: Any) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip().upper()
        if not text or text in unique:
            continue
        unique.append(text)
    return unique


def _unique_ordered(values: Any) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in unique:
            continue
        unique.append(text)
    return unique
