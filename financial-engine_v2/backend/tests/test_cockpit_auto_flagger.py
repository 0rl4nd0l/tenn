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


def test_detect_auto_flag_findings_ignores_sourceable_compacted_youtube_rows() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "Recent videos: Audeara 2026 March Quarterly (4C).",
            "routing_metadata": {"latency_ms": 1200},
            "tool_traces": [
                {
                    "tool": "check_youtube_channel_recent_videos",
                    "ok": True,
                    "duration_ms": 800,
                }
            ],
            "evidence": [
                {
                    "tool": "check_youtube_channel_recent_videos",
                    "result": {
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 3245,
                        "name": "Kneppy Invests",
                        "channel_id": "UCjQJPzeCJhA4KrETh3FVVHA",
                        "videos": [
                            {
                                "title": "Audeara 2026 March Quarterly (4C)",
                                "video_id": "2LOaEmbMkY0",
                                "webpage_url": "https://www.youtube.com/watch?v=2LOaEmbMkY0",
                                "duration_seconds": 373,
                            }
                        ],
                    },
                }
            ],
        }
    )

    assert findings == []


def test_detect_auto_flag_findings_ignores_sourceable_compacted_ingest_rows() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "Staged selected YouTube transcript for review.",
            "routing_metadata": {"latency_ms": 1200},
            "tool_traces": [
                {
                    "tool": "ingest_youtube_videos",
                    "ok": True,
                    "duration_ms": 900,
                }
            ],
            "evidence": [
                {
                    "tool": "ingest_youtube_videos",
                    "result": {
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 2570,
                        "results": [
                            {
                                "video_title": "Audeara 2026 March Quarterly (4C)",
                                "source_id": "youtube_transcript:audeara:abc123",
                                "video_id": "2LOaEmbMkY0",
                                "webpage_url": "https://www.youtube.com/watch?v=2LOaEmbMkY0",
                            }
                        ],
                    },
                }
            ],
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
