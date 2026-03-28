from __future__ import annotations

from typing import Any


_TOOL_ACTION_ID_MAP: dict[str, str] = {
    "run_backfill": "single_ticker_announcement_backfill",
    "run_metric_extraction": "metric_extraction",
    "run_news_ingest": "daily_news_ingest",
    "run_announcement_ingest": "daily_announcement_ingest",
    "update_financials": "update_ticker_financials",
    "rebuild_financials": "rebuild_ticker_financials",
    "audit_financials": "audit_ticker_financials",
    "generate_chart": "show_candlestick",
}


def normalize_action_preview(preview: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(preview or {})
    tool = str(source.get("tool") or "").strip()
    args = source.get("args")
    if not isinstance(args, dict):
        args = source.get("arguments")
    normalized_args = dict(args or {})

    normalized: dict[str, Any] = {
        "action_id": source.get("action_id") or _TOOL_ACTION_ID_MAP.get(tool),
        "args": normalized_args,
    }
    if tool:
        normalized["tool"] = tool

    for key in (
        "action_label",
        "explanation",
        "requires_confirmation",
        "is_mutating",
        "timeout_seconds",
        "command",
        "impact",
        "resume_message",
        "scope",
    ):
        if key in source:
            normalized[key] = source[key]

    if "arguments" in source:
        normalized["arguments"] = dict(source.get("arguments") or {})

    return normalized
