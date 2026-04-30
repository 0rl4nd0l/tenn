from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any


LATENCY_WARNING_MS = 45_000
SLOW_TOOL_WARNING_MS = 20_000
TOOL_COUNT_WARNING = 6

_TIMEOUT_RE = re.compile(r"\b(time(?:d)?\s*out|timeout|deadline|watchdog expired)\b", re.IGNORECASE)
_ERROR_RE = re.compile(r"\b(error|failed|failure|unavailable|not configured|backend down)\b", re.IGNORECASE)
_INABILITY_RE = re.compile(
    r"\b("
    r"can(?:not|'t)\s+(?:verify|confirm|access|retrieve)|"
    r"unable\s+to\s+(?:verify|access|retrieve)|"
    r"not enough (?:evidence|sources|information)|"
    r"no (?:canonical )?(?:financial|source|data|rows?)"
    r")\b",
    re.IGNORECASE,
)
_CONTEXT_COMPACTION_RE = re.compile(
    r"(_truncated|_original_chars|additional fields omitted|summarized\s+[—-]\s+original)",
    re.IGNORECASE,
)
_SOURCE_LIST_KEYS = frozenset(
    {
        "hits",
        "results",
        "documents",
        "context",
        "alerts",
        "videos",
        "docs",
        "doc_snippets",
        "announcement_context",
        "financials",
    }
)
_SOURCE_ID_KEYS = frozenset(
    {
        "url",
        "source_url",
        "webpage_url",
        "source_id",
        "document_id",
        "source_document_id",
        "path",
        "video_id",
    }
)
_SOURCE_TEXT_KEYS = frozenset(
    {"title", "video_title", "source_name", "name", "snippet", "text", "excerpt"}
)


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _to_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _json_preview(value: Any, limit: int = 1200) -> str:
    try:
        text = json.dumps(value, default=str, sort_keys=True)
    except (TypeError, ValueError):
        text = str(value)
    return text[:limit]


def _has_sourceable_compacted_rows(result: Any) -> bool:
    """Return true when truncation preserved source rows usable by the UI."""
    if not isinstance(result, dict):
        return False
    for key in _SOURCE_LIST_KEYS:
        rows = result.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            has_identity = any(row.get(field) not in (None, "") for field in _SOURCE_ID_KEYS)
            has_text = any(row.get(field) not in (None, "") for field in _SOURCE_TEXT_KEYS)
            if has_identity and has_text:
                return True
    return False


def _has_sourceable_price_observation(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    price = result.get("price") if isinstance(result.get("price"), dict) else {}
    if result.get("ok") is False or price.get("ok") is False:
        return False
    current = price.get("current") if isinstance(price.get("current"), dict) else {}
    provider = str(price.get("provider") or "").strip()
    symbol = str(price.get("symbol") or result.get("ticker") or "").strip()
    return bool(provider and symbol and current.get("price") is not None)


def _append(
    findings: list[dict[str, Any]],
    *,
    category: str,
    severity: str,
    reason: str,
    evidence: dict[str, Any] | None = None,
) -> None:
    key = (category, reason)
    if any((item.get("category"), item.get("reason")) == key for item in findings):
        return
    findings.append(
        {
            "category": category,
            "severity": severity,
            "reason": reason,
            "evidence": evidence or {},
        }
    )


def _result_has_error(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None
    if result.get("ok") is False:
        return str(result.get("error") or "tool returned ok=false")
    for key in ("error", "db_error", "company_error", "news_error"):
        text = str(result.get(key) or "").strip()
        if text:
            return text
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(item) for item in errors[:3])
    return None


def detect_auto_flag_findings(turn: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic Cockpit diagnostics worth saving as auto flags.

    This intentionally inspects only operational evidence already produced by a
    chat turn. It does not retrieve data, rank sources, or judge financial truth.
    """

    findings: list[dict[str, Any]] = []
    if not isinstance(turn, dict):
        return findings

    response_text = str(turn.get("response_text") or "")
    routing = turn.get("routing_metadata") if isinstance(turn.get("routing_metadata"), dict) else {}
    evidence = _dicts(turn.get("evidence"))
    tool_traces = _dicts(turn.get("tool_traces"))
    status_events = _dicts(turn.get("status_events"))

    if routing.get("grounding_guard") == "missing_visible_sources":
        _append(
            findings,
            category="missing_sources",
            severity="high",
            reason="Source contract guard replaced the answer because no visible sources were available.",
            evidence={"tool_audit": routing.get("tool_audit") or []},
        )

    latency_ms = _to_int(routing.get("latency_ms"))
    if latency_ms is not None and latency_ms >= LATENCY_WARNING_MS:
        _append(
            findings,
            category="inefficiency",
            severity="medium",
            reason=f"Chat turn latency exceeded {LATENCY_WARNING_MS}ms.",
            evidence={"latency_ms": latency_ms},
        )

    if len(tool_traces) >= TOOL_COUNT_WARNING:
        _append(
            findings,
            category="inefficiency",
            severity="medium",
            reason=f"Chat turn executed {len(tool_traces)} tool calls.",
            evidence={"tool_count": len(tool_traces)},
        )

    for trace in tool_traces:
        tool = str(trace.get("tool") or trace.get("tool_name") or "unknown_tool")
        error_text = str(trace.get("error") or "").strip()
        if trace.get("ok") is False or error_text:
            _append(
                findings,
                category="tool_failure",
                severity="high",
                reason=f"Tool {tool} failed during the chat turn.",
                evidence={
                    "tool": tool,
                    "error": error_text or "ok=false",
                    "hint": trace.get("hint"),
                },
            )
        duration_ms = _to_int(trace.get("duration_ms"))
        if duration_ms is not None and duration_ms >= SLOW_TOOL_WARNING_MS:
            _append(
                findings,
                category="inefficiency",
                severity="medium",
                reason=f"Tool {tool} took at least {SLOW_TOOL_WARNING_MS}ms.",
                evidence={"tool": tool, "duration_ms": duration_ms},
            )

    for item in evidence:
        tool = str(item.get("tool") or item.get("type") or "evidence")
        result = item.get("result") if "result" in item else item.get("details")
        result_error = _result_has_error(result)
        if result_error:
            _append(
                findings,
                category="information_access",
                severity="high",
                reason=f"Evidence source {tool} reported an access or data error.",
                evidence={"tool": tool, "error": result_error[:400]},
            )
        if _CONTEXT_COMPACTION_RE.search(_json_preview(item)) and not (
            isinstance(result, dict)
            and (
                _has_sourceable_compacted_rows(result)
                or _has_sourceable_price_observation(result)
            )
        ):
            _append(
                findings,
                category="context_truncation",
                severity="medium",
                reason=f"Evidence source {tool} carried context compaction metadata.",
                evidence={"tool": tool},
            )

    for event in status_events:
        stage = str(event.get("stage") or "")
        if _TIMEOUT_RE.search(stage):
            _append(
                findings,
                category="timeout",
                severity="high",
                reason="Status events indicate a timeout or watchdog expiry.",
                evidence={"stage": stage[:400]},
            )
        elif _ERROR_RE.search(stage):
            _append(
                findings,
                category="information_access",
                severity="medium",
                reason="Status events indicate an error or unavailable dependency.",
                evidence={"stage": stage[:400]},
            )

    if _CONTEXT_COMPACTION_RE.search(response_text):
        _append(
            findings,
            category="context_truncation",
            severity="high",
            reason="Final response mentioned internal truncation or compaction metadata.",
            evidence={"response_excerpt": response_text[:400]},
        )

    if _INABILITY_RE.search(response_text) and any(
        item.get("category") in {"tool_failure", "information_access", "missing_sources", "timeout"}
        for item in findings
    ):
        _append(
            findings,
            category="information_access",
            severity="medium",
            reason="Final response said Tenn could not verify or access requested information after diagnostics showed a related issue.",
            evidence={"response_excerpt": response_text[:400]},
        )

    return findings[:10]


def build_auto_flag_note(findings: list[dict[str, Any]]) -> str:
    categories = []
    for item in findings:
        category = str(item.get("category") or "").strip()
        if category and category not in categories:
            categories.append(category)
    if not categories:
        return "Auto diagnostic flag"
    return "Auto diagnostic flag: " + ", ".join(categories[:6])


def build_auto_flag_fingerprint(
    *,
    thread_id: str,
    response_text: str,
    findings: list[dict[str, Any]],
) -> str:
    payload = {
        "thread_id": thread_id,
        "response_text": str(response_text or "")[:500],
        "categories": [item.get("category") for item in findings],
        "reasons": [item.get("reason") for item in findings],
    }
    return sha256(json.dumps(payload, default=str, sort_keys=True).encode("utf-8")).hexdigest()
