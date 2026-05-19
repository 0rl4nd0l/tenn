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


def test_detect_auto_flag_findings_catches_missing_model_for_known_source() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "Here is a response.",
            "routing_metadata": {"source": "orchestrator", "model": None},
            "evidence": [],
        }
    )

    assert any(item["category"] == "routing_provenance" for item in findings)
    assert any("did not identify the model" in item["reason"] for item in findings)


def test_detect_auto_flag_findings_catches_force_api_local_contradiction() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "Here is a response.",
            "routing_metadata": {
                "source": "local",
                "model": "model:qwen",
                "routing_reason": "force:api",
            },
            "evidence": [],
        }
    )

    assert any(item["category"] == "routing_provenance" for item in findings)
    assert any("required API" in item["reason"] for item in findings)


def test_detect_auto_flag_findings_catches_substantive_missing_visible_sources() -> None:
    findings = detect_auto_flag_findings(
        {
            "request": {"message": "tell me about BHP"},
            "response_text": "I can't verify that from current evidence.",
            "routing_metadata": {
                "source": "local",
                "model": "model:test",
                "grounding_guard": "missing_visible_sources",
            },
            "evidence": [],
        }
    )

    assert any(item["category"] == "missing_sources" for item in findings)


def test_detect_auto_flag_findings_ignores_control_prompt_missing_visible_sources_only() -> None:
    findings = detect_auto_flag_findings(
        {
            "request": {"message": "Reply exactly: ok"},
            "response_text": "I can't verify that from current evidence.",
            "routing_metadata": {
                "source": "local",
                "model": "model:test",
                "grounding_guard": "missing_visible_sources",
            },
            "evidence": [],
            "tool_traces": [],
            "status_events": [],
        }
    )

    assert findings == []


def test_detect_auto_flag_findings_catches_generic_orchestrator_memory() -> None:
    findings = detect_auto_flag_findings(
        {
            "request": {"message": "Reply exactly ok."},
            "response_text": "ok\n\nCoverage and Failure Signals:",
            "routing_metadata": {
                "source": "orchestrator",
                "model": "claude-sonnet-test",
            },
            "evidence": [
                {
                    "type": "orchestrator",
                    "details": {
                        "intent": "mixed",
                        "source_plan": ["financial_truth", "market_memory"],
                        "entities": {
                            "primary_ticker": None,
                            "tickers": [],
                            "sector": None,
                        },
                    },
                },
                {
                    "type": "market_memory",
                    "tool": "market_memory",
                    "result": {
                        "items": [
                            {
                                "type": "macro_theme",
                                "statement": "Australian inflation gauge has cooled.",
                            }
                        ]
                    },
                },
            ],
        }
    )

    assert any(item["category"] == "evidence_relevance" for item in findings)
    assert any("generic/control prompt" in item["reason"] for item in findings)


def test_detect_auto_flag_findings_allows_scoped_orchestrator_memory() -> None:
    findings = detect_auto_flag_findings(
        {
            "request": {"message": "analyse BHP"},
            "response_text": "BHP answer with visible sources.",
            "routing_metadata": {
                "source": "orchestrator",
                "model": "claude-sonnet-test",
            },
            "evidence": [
                {
                    "type": "orchestrator",
                    "details": {
                        "intent": "mixed",
                        "source_plan": ["financial_truth", "market_memory"],
                        "entities": {
                            "primary_ticker": "BHP",
                            "tickers": ["BHP"],
                            "sector": "Materials",
                        },
                    },
                }
            ],
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


def test_detect_auto_flag_findings_ignores_sourceable_compacted_company_rows() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "EOS is described from company documents.",
            "routing_metadata": {"latency_ms": 1200},
            "tool_traces": [
                {
                    "tool": "get_company_dump",
                    "ok": True,
                    "duration_ms": 700,
                }
            ],
            "evidence": [
                {
                    "tool": "get_company_dump",
                    "result": {
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 18_000,
                        "docs": [
                            {
                                "title": "EOS annual report",
                                "source_url": "https://example.com/eos-annual.pdf",
                                "document_id": "doc-annual",
                            }
                        ],
                        "doc_snippets": [
                            {
                                "title": "Business overview",
                                "source_url": "https://example.com/eos-overview.pdf",
                                "snippet": "EOS describes defence and space systems operations.",
                            }
                        ],
                    },
                }
            ],
        }
    )

    assert findings == []


def test_detect_auto_flag_findings_ignores_sourceable_compacted_price_observation() -> None:
    findings = detect_auto_flag_findings(
        {
            "response_text": "PPT price data is available.",
            "routing_metadata": {"latency_ms": 1200},
            "tool_traces": [
                {
                    "tool": "get_price",
                    "ok": True,
                    "duration_ms": 200,
                }
            ],
            "evidence": [
                {
                    "tool": "get_price",
                    "result": {
                        "ok": True,
                        "_truncated": True,
                        "_original_chars": 44_381,
                        "ticker": "PPT",
                        "price": {
                            "provider": "yahoo_finance",
                            "symbol": "PPT.AX",
                            "range": "1y",
                            "interval": "1d",
                            "current": {
                                "price": 16.57,
                                "market_time": "2026-04-30T06:10:06+00:00",
                            },
                        },
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
