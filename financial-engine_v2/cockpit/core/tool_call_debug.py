"""Structured diagnostics for agent tool calls (cockpit agent loop).

Used for in-chat debug lines and logging. Does not invoke the LLM.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_RE = re.compile(
    r"(key|token|secret|password|auth|api_key)", re.IGNORECASE
)


def summarize_arguments_for_log(arguments: dict[str, Any] | None, *, max_len: int = 160) -> str:
    """Compact, log-safe representation of tool arguments."""
    if not arguments:
        return "{}"
    parts: list[str] = []
    for k, v in list(arguments.items())[:12]:
        ks = str(k)
        if _SENSITIVE_KEY_RE.search(ks):
            parts.append(f"{ks}=<redacted>")
            continue
        vs = v if isinstance(v, (str, int, float, bool)) or v is None else json.dumps(v, default=str)[:80]
        s = f"{ks}={vs}"
        if len(s) > 72:
            s = s[:69] + "…"
        parts.append(s)
    out = ", ".join(parts)
    if len(arguments) > 12:
        out += ", …"
    if len(out) > max_len:
        out = out[: max_len - 1] + "…"
    return out


def tool_result_succeeded(result: dict[str, Any]) -> bool:
    """Return False if the tool payload indicates failure."""
    if result.get("ok") is True:
        return True
    if result.get("ok") is False:
        return False
    if "error" in result:
        return False
    return True


def extract_error_message(result: dict[str, Any]) -> str:
    err = result.get("error")
    if err is not None:
        return str(err)[:800]
    if result.get("ok") is False:
        return str(result.get("message") or result.get("detail") or "unknown failure (ok=false)")[:800]
    return ""


def failure_hint(tool_name: str, result: dict[str, Any]) -> str:
    """Short remediation hint for operators (not for the LLM)."""
    err = extract_error_message(result).lower()
    if "unknown tool" in err:
        return "Check the tool name against cockpit tool definitions / spelling."
    if "backend" in err or "connection" in err or "unreachable" in err or "timeout" in err:
        return "Verify backend API is running and COCKPIT_BACKEND / api_base_url is correct."
    if "ticker is required" in err or "ticker" in err and "required" in err:
        return "Provide a ticker in arguments or set chat context."
    if "not available" in err or "not configured" in err:
        return "Feature may need env keys, backend URL, or RAG toggles in Ops settings."
    if tool_name in {"query_ticker_data", "get_price", "search_documents"}:
        return "Confirm ticker symbol and that data exists for that company."
    return "See cockpit logs at DEBUG for full traceback if this was an exception."


def build_tool_trace_entry(
    *,
    iteration: int,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    duration_ms: float,
) -> dict[str, Any]:
    """Single structured record for UI + logging."""
    ok = tool_result_succeeded(result)
    err = "" if ok else extract_error_message(result)
    return {
        "iteration": iteration,
        "tool": tool_name,
        "arguments_summary": summarize_arguments_for_log(arguments),
        "ok": ok,
        "error": err,
        "duration_ms": round(duration_ms, 2),
        "hint": "" if ok else failure_hint(tool_name, result),
    }


def format_trace_for_chat_line(entry: dict[str, Any]) -> str:
    """One human-readable line for RichLog (no markdown tables)."""
    it = entry.get("iteration", "?")
    name = entry.get("tool", "?")
    args_s = entry.get("arguments_summary", "")
    ms = entry.get("duration_ms", 0)
    if entry.get("ok"):
        return f"  [tools] iter {it} {name}({args_s}) ok in {ms}ms"
    err = entry.get("error") or "failed"
    hint = entry.get("hint") or ""
    return f"  [tools] iter {it} {name}({args_s}) FAILED: {err} — {hint}"


def format_failure_block(traces: list[dict[str, Any]], *, include_success: bool) -> str:
    """Multi-line block appended under assistant reply when debug is on."""
    lines = []
    for t in traces:
        if not include_success and t.get("ok"):
            continue
        lines.append(format_trace_for_chat_line(t))
    if not lines:
        return ""
    header = "[Tool trace]" if include_success else "[Tool failures]"
    return header + "\n" + "\n".join(lines)


def cockpit_tool_chat_debug_mode() -> tuple[bool, bool]:
    """Return (show_failures_in_chat, show_full_trace_in_chat).

    * ``COCKPIT_TOOL_DEBUG`` — ``off`` suppresses chat lines; ``1``/``all`` shows
      every tool call; unset or ``failures`` shows only failed tools (default).
    """
    raw = (os.environ.get("COCKPIT_TOOL_DEBUG") or "").strip().lower()
    if raw in {"0", "false", "no", "off", "none"}:
        return False, False
    if raw in {"1", "true", "yes", "all", "full"}:
        return True, True
    # default: failures only
    return True, False
