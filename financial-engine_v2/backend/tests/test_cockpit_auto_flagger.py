from __future__ import annotations

from app.services.cockpit_auto_flagger import (
    build_auto_flag_fingerprint,
    build_auto_flag_note,
    detect_auto_flag_findings,
)


def test_detect_auto_flag_findings_catches_failure_truncation_and_latency() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "I can't verify that from current evidence.",
            "routing_metadata": {
                "latency_ms": 52_000,
                "grounding_guard": "missing_visible_sources",
                "tool_audit": [{"tool": "search_news", "hit_count": 0}],
            },
            "tool_traces": [
                {
                    "tool": "get_financials",
                    "ok": False,
                    "error": "backend API client not configured",
                    "duration_ms": 21_000,
                }
            ],
            "evidence": [
                {
                    "tool": "query_ticker_data",
                    "result": {"ok": True, "_truncated": True},
                }
            ],
        }
    )

    categories = {item["category"] for item in findings}
    assert {
        "missing_sources",
        "tool_failure",
        "context_truncation",
        "information_access",
        "inefficiency",
    } <= categories
    assert build_auto_flag_note(findings).startswith("Auto diagnostic flag:")


def test_detect_auto_flag_findings_ignores_clean_turn() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "BHP answer with visible sources.",
            "routing_metadata": {"latency_ms": 1200},
            "tool_traces": [{"tool": "query_ticker_data", "ok": True, "duration_ms": 50}],
            "evidence": [{"tool": "query_ticker_data", "result": {"ok": True}}],
        }
    )

    assert findings == []


def test_auto_flag_fingerprint_is_stable_for_same_findings() -> None:
    findings = [{"category": "tool_failure", "reason": "Tool failed."}]

    first = build_auto_flag_fingerprint(
        thread_id="session-1",
        response_text="I cannot access that.",
        findings=findings,
    )
    second = build_auto_flag_fingerprint(
        thread_id="session-1",
        response_text="I cannot access that.",
        findings=findings,
    )

    assert first == second
