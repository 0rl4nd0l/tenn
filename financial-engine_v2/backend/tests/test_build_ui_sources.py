from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import _build_ui_sources


def test_orchestrator_format_local_context() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "local_context",
                "details": {
                    "qual_context": {
                        "hits": [
                            {
                                "title": "Quarterly filing",
                                "url": "https://example.com/q4.pdf",
                                "text": "Cash increased during the quarter.",
                                "document_id": "doc-001",
                            }
                        ]
                    }
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Quarterly filing"
    assert sources[0]["kind"] == "rag"


def test_local_context_price_query_renders_visible_source() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "local_context",
                "details": {
                    "price_query": {
                        "ticker": "JBH",
                        "kind": "current",
                        "close": 112.34,
                        "date": "2026-04-30",
                    }
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "JBH current price"
    assert sources[0]["source_id"] == "price_query:JBH:2026-04-30"
    assert sources[0]["published_at"] == "2026-04-30"
    assert "close: 112.34" in str(sources[0]["snippet"])


def test_ingest_youtube_videos_renders_visible_source() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "ingest_youtube_videos",
                "result": {
                    "results": [
                        {
                            "video_title": "JBH channel thesis",
                            "video_id": "abc123",
                            "webpage_url": "https://www.youtube.com/watch?v=abc123",
                            "published_at": "2026-04-29T10:00:00Z",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "JBH channel thesis"
    assert sources[0]["source_id"] == "youtube:abc123"
    assert sources[0]["url"] == "https://www.youtube.com/watch?v=abc123"
    assert sources[0]["kind"] == "web"


def test_orchestrator_financial_truth_announcement_context_renders_visible_sources() -> None:
    financial_truth = {
        "source": "financial_truth",
        "status": "ok",
        "ticker": "PPT",
        "items": [],
        "announcement_context": [
            {
                "document_id": "ppt-sale-doc",
                "ticker": "PPT",
                "published_at": "2026-03-16",
                "title": "Sale of Wealth Management business",
                "pdf_path": "/tmp/ppt-sale.pdf",
                "excerpt": "PPT announced the sale of its Wealth Management business.",
                "context_source": "cockpit_announcement_context",
            }
        ],
        "docs": [
            {
                "document_id": "ppt-sale-doc",
                "ticker": "PPT",
                "published_at": "2026-03-16",
                "title": "Sale of Wealth Management business",
                "source_url": "https://example.com/ppt-sale.pdf",
                "pdf_path": "/tmp/ppt-sale.pdf",
            }
        ],
    }

    sources = _build_ui_sources(
        [
            {
                "type": "financial_truth",
                "tool": "financial_truth",
                "details": financial_truth,
                "result": financial_truth,
            }
        ]
    )

    assert len(sources) == 2
    assert sources[0]["title"] == "Sale of Wealth Management business"
    assert sources[0]["kind"] == "document"
    assert sources[0]["url"] is None
    assert sources[0]["document_id"] == "ppt-sale-doc"
    assert sources[0]["path"] == "/tmp/ppt-sale.pdf"
    assert "Wealth Management business" in str(sources[0]["snippet"])
    assert sources[1]["url"] == "https://example.com/ppt-sale.pdf"


def test_orchestrator_nested_financial_truth_financial_rows_render_visible_sources() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "orchestrator",
                "details": {
                    "financial_truth": {
                        "ticker": "BHP",
                        "financials": [
                            {
                                "ticker": "BHP",
                                "period_type": "annual",
                                "period_end": "2025-06-30",
                                "revenue": 55100,
                                "source_document_id": "doc-bhp-fy25",
                            }
                        ],
                        "latest_financial_snapshot": {
                            "ticker": "BHP",
                            "period_type": "annual",
                            "period_end": "2025-06-30",
                            "cash_end": 9000,
                            "source_document_id": "doc-bhp-fy25-snapshot",
                        },
                    }
                },
            }
        ]
    )

    assert len(sources) == 2
    assert sources[0]["title"] == "BHP annual 2025-06-30"
    assert sources[0]["document_id"] == "doc-bhp-fy25"
    assert "revenue: 55100" in str(sources[0]["snippet"])
    assert sources[1]["document_id"] == "doc-bhp-fy25-snapshot"


def test_orchestrator_memory_payloads_render_visible_sources() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "orchestrator",
                "details": {
                    "company_memory": {
                        "items": [
                            {
                                "entry_id": 7,
                                "type": "strategy",
                                "statement": "Management is prioritising copper growth.",
                                "confidence": 0.8,
                                "updated_at": "2026-04-20T00:00:00+00:00",
                            }
                        ]
                    },
                    "market_memory": {
                        "items": [
                            {
                                "entry_id": 3,
                                "type": "macro",
                                "statement": "Iron ore pricing remains volatile.",
                                "confidence": 0.7,
                            }
                        ]
                    },
                    "user_thesis_memory": {
                        "items": [
                            {
                                "entry_id": 2,
                                "entry_type": "watch",
                                "statement": "Wait for balance-sheet confirmation.",
                                "confidence": 0.6,
                            }
                        ]
                    },
                },
            }
        ]
    )

    assert [source["source_id"] for source in sources] == [
        "company_memory:7",
        "market_memory:3",
        "user_thesis_memory:2",
    ]
    assert "copper growth" in str(sources[0]["snippet"])


def test_agent_format_search_news() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_news",
                "result": {
                    "hits": [
                        {
                            "title": "BHP news",
                            "url": "https://news.example.com/bhp",
                            "snippet": "BHP announced an update.",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["kind"] == "news"
    assert sources[0]["url"] == "https://news.example.com/bhp"


def test_agent_format_search_news_zero_hits_emits_operational_source_item() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_news",
                "result": {
                    "query": "BHP news",
                    "ticker": "BHP",
                    "hit_count": 0,
                    "hits": [],
                    "freshness_warning": "News index last updated 2 days ago.",
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "News search: no hits for BHP news"
    assert sources[0]["source_id"] == "search_news:no_hits:bhp news"
    assert sources[0]["doc_type"] == "operational_no_hit"
    assert "2 days ago" in str(sources[0]["snippet"])


def test_agent_format_get_price_uses_nested_symbol_for_source_identity() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_price",
                "result": {
                    "ok": True,
                    "price": {
                        "symbol": "CBA.AX",
                        "range": "1y",
                        "interval": "1d",
                        "provider": "yahoo",
                        "current": {"market_time": "2026-04-30T06:18:24+00:00"},
                    },
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "CBA price data"
    assert sources[0]["source_id"] == "price:CBA:1y:1d"
    assert "Provider: yahoo" in str(sources[0]["snippet"])


def test_agent_format_get_price_skips_failed_nested_price_payload() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_price",
                "result": {
                    "ok": False,
                    "ticker": "XJO",
                    "price": {
                        "ok": False,
                        "ticker": "XJO",
                        "range": "1d",
                        "interval": "1d",
                        "error": "market price provider returned HTTP 404",
                    },
                    "price_state": {
                        "ok": False,
                        "ticker": "XJO",
                        "last_close": None,
                        "error": "market price provider returned HTTP 404",
                    },
                },
            }
        ]
    )

    assert sources == []


def test_agent_format_gather_local_context() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "gather_local_context",
                "result": {
                    "rag_hits": [
                        {
                            "title": "Results deck",
                            "url": "https://example.com/deck.pdf",
                            "text": "Margin expanded 120 bps.",
                            "document_id": "doc-002",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["kind"] == "rag"
    assert sources[0]["document_id"] == "doc-002"


def test_empty_evidence_list() -> None:
    assert _build_ui_sources([]) == []


def test_non_dict_evidence_entry() -> None:
    sources = _build_ui_sources(
        [
            "bad-entry",
            {
                "tool": "search_news",
                "result": {"hits": [{"title": "Safe", "url": "https://example.com"}]},
            },
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Safe"


def test_runtime_clock_evidence_renders_visible_source() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "runtime_clock",
                "details": {
                    "title": "Cockpit runtime clock",
                    "source_id": "runtime_clock:australia-sydney",
                    "snippet": "Backend runtime clock in Australia/Sydney reported 2026-04-18T11:36:00+10:00.",
                    "published_at": "2026-04-18T11:36:00+10:00",
                },
            }
        ]
    )

    assert sources == [
        {
            "title": "Cockpit runtime clock",
            "score": 0.0,
            "url": None,
            "snippet": "Backend runtime clock in Australia/Sydney reported 2026-04-18T11:36:00+10:00.",
            "published_at": "2026-04-18T11:36:00+10:00",
            "document_id": None,
            "source_id": "runtime_clock:australia-sydney",
            "doc_type": None,
            "path": None,
            "kind": "context",
        }
    ]


def test_agent_format_search_announcements() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_announcements",
                "result": {
                    "documents": [
                        {
                            "title": "Half-year results",
                            "source_url": "https://example.com/hy.pdf",
                            "document_id": "doc-hy",
                        }
                    ],
                    "context": [
                        {
                            "title": "Management commentary",
                            "excerpt": "Revenue improved in the half.",
                            "document_id": "ctx-hy",
                        }
                    ],
                },
            }
        ]
    )

    assert [source["title"] for source in sources] == [
        "Half-year results",
        "Management commentary",
    ]


def test_agent_format_get_financials() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_financials",
                "result": {
                    "ticker": "BHP",
                    "narrative": "Revenue grew year over year.",
                    "financials": [
                        {
                            "ticker": "BHP",
                            "period_type": "annual",
                            "period_end": "2025-06-30",
                            "source_document_id": "doc-fin-1",
                        }
                    ],
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["document_id"] == "doc-fin-1"
    assert sources[0]["doc_type"] == "annual"
    assert "Revenue grew" in str(sources[0]["snippet"])


def test_agent_format_recall_dossier() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "recall_dossier",
                "result": {
                    "findings": [
                        {
                            "source": "Broker note",
                            "source_url": "https://example.com/broker",
                            "finding": "Iron ore volumes remain resilient.",
                            "confidence": 0.8,
                            "ts": "2026-04-14T10:00:00+00:00",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Broker note"
    assert sources[0]["url"] == "https://example.com/broker"
    assert "resilient" in str(sources[0]["snippet"])


def test_agent_format_deep_research() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "deep_research",
                "result": {
                    "ticker": "BHP",
                    "research": {
                        "summary": "Diversified cash generation remains solid.",
                        "confidence": 0.72,
                    },
                },
            }
        ]
    )

    assert sources == [
        {
            "title": "Deep research brief",
            "score": 0.72,
            "url": None,
            "snippet": "Diversified cash generation remains solid.",
            "published_at": None,
            "document_id": None,
            "source_id": "deep_research:BHP",
            "doc_type": None,
            "path": None,
            "kind": "context",
        }
    ]


def test_agent_format_search_web() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_web",
                "result": {
                    "results": [
                        {
                            "title": "Investor day transcript",
                            "url": "https://example.com/transcript",
                            "snippet": "Management discussed copper demand.",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["kind"] == "web"


def test_holdings_evidence_renders_visible_sources() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "holdings",
                "details": [
                    {
                        "holding_id": "h-1",
                        "ticker": "EIQ",
                        "account_label": "COMMSEC LT",
                        "quantity": 5700.0,
                        "avg_cost": 0.26,
                    }
                ],
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "EIQ holding"
    assert sources[0]["source_id"] == "h-1"
    assert "Quantity: 5700.0" in str(sources[0]["snippet"])


def test_watchlist_evidence_renders_visible_sources() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "watchlist",
                "details": [
                    {"ticker": "BHP", "added_at": "2026-04-21T00:00:00+00:00"}
                ],
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP watchlist"
    assert sources[0]["source_id"] == "watchlist:BHP"
    assert "Added: 2026-04-21" in str(sources[0]["snippet"])


def test_market_update_evidence_uses_report_date_and_full_confidence() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "market_update_report",
                "details": {
                    "report_id": "report-1",
                    "run_type": "final",
                    "report_date": "2026-04-29",
                    "status": "partial",
                    "summary": {
                        "movers": [{"ticker": "BHP"}],
                        "tickers": [{"ticker": "BHP"}, {"ticker": "RIO"}],
                    },
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Market update 2026-04-29"
    assert sources[0]["source_id"] == "market_update:2026-04-29"
    assert sources[0]["score"] == 1.0
    assert "1 mover(s)" in str(sources[0]["snippet"])
    assert "2 ticker(s) scanned" in str(sources[0]["snippet"])


def test_agent_format_fetch_url() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "fetch_url",
                "result": {
                    "url": "https://example.com/article",
                    "content": "A long article body appears here.",
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Fetched page"
    assert sources[0]["snippet"] == "A long article body appears here."


def test_agent_format_get_data_quality() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_data_quality",
                "result": {
                    "recent_failures": [
                        {
                            "title": "Failed filing",
                            "document_id": "doc-fail-1",
                            "error": "parser error",
                        }
                    ],
                    "recent_low_conf_rows": [
                        {
                            "ticker": "BHP",
                            "period_type": "annual",
                            "period_end": "2025-06-30",
                            "source_document_id": "doc-low-1",
                            "confidence_metrics": 0.2,
                        }
                    ],
                },
            }
        ]
    )

    assert len(sources) == 2
    assert sources[0]["document_id"] == "doc-fail-1"
    assert sources[1]["document_id"] == "doc-low-1"


def test_agent_format_run_analysis() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "run_analysis",
                "result": {
                    "ticker": "BHP",
                    "modules": [
                        {
                            "module": "valuation",
                            "status": "complete",
                            "metrics": {"P/E": 12.3},
                            "narrative": "Valuation looks reasonable.",
                        }
                    ],
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "valuation analysis"
    assert sources[0]["source_id"] == "analysis:BHP:valuation"


def test_agent_format_get_price() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_price",
                "result": {
                    "ticker": "BHP",
                    "price": {
                        "provider": "yfinance",
                        "range": "1y",
                        "interval": "1d",
                        "current": {"market_time": "2026-04-15T00:00:00Z"},
                    },
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP price data"
    assert sources[0]["source_id"] == "price:BHP:1y:1d"


def test_agent_format_get_price_on_date() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_price_on_date",
                "result": {
                    "ticker": "BHP",
                    "date": "2026-04-01",
                    "open": 40.0,
                    "high": 42.0,
                    "low": 39.5,
                    "close": 41.5,
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP price on 2026-04-01"
    assert "close 41.5" in str(sources[0]["snippet"])


def test_agent_format_get_price_range() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_price_range",
                "result": {
                    "ticker": "BHP",
                    "start_date": "2026-04-01",
                    "end_date": "2026-04-10",
                    "data_points": 7,
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP price range 2026-04-01 to 2026-04-10"
    assert "7 price observations" in str(sources[0]["snippet"])


def test_agent_format_search_social() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_social",
                "result": {
                    "stories": [
                        {
                            "title": "Thread on copper demand",
                            "url": "https://news.ycombinator.com/item?id=1",
                            "snippet": "Investors debated copper demand signals.",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Thread on copper demand"
    assert sources[0]["kind"] == "web"


def test_agent_format_check_youtube_channel_recent_videos() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "check_youtube_channel_recent_videos",
                "result": {
                    "ok": True,
                    "name": "Kneppy Invests",
                    "channel_id": "UCabc123",
                    "videos": [
                        {
                            "video_id": "vid123",
                            "title": "BHP quarterly results breakdown",
                            "published_at": "2026-04-28T00:00:00Z",
                            "webpage_url": "https://www.youtube.com/watch?v=vid123",
                            "duration_seconds": 1200,
                            "scores": {"overall": 0.91},
                        },
                        {
                            "video_id": "vid456",
                            "title": "RIO update",
                            "published_at": "2026-04-27T00:00:00Z",
                        },
                    ],
                },
            }
        ]
    )

    assert len(sources) == 2
    assert sources[0]["title"] == "BHP quarterly results breakdown"
    assert sources[0]["url"] == "https://www.youtube.com/watch?v=vid123"
    assert sources[0]["source_id"] == "youtube:vid123"
    assert sources[0]["published_at"] == "2026-04-28T00:00:00Z"
    assert sources[0]["doc_type"] == "youtube_video"
    assert "Video ID: vid123" in str(sources[0]["snippet"])
    assert sources[1]["url"] == "https://www.youtube.com/watch?v=vid456"


def test_agent_format_get_watchlist_alerts() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_watchlist_alerts",
                "result": {
                    "alerts": [
                        {
                            "id": "alert-1",
                            "ticker": "BHP",
                            "type": "price",
                            "message": "Single-day return breached threshold.",
                            "ts": "2026-04-15T09:00:00+00:00",
                        }
                    ]
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP price"
    assert sources[0]["source_id"] == "alert-1"


def test_agent_format_get_watchlist_alerts_without_rows_still_emits_source_item() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_watchlist_alerts",
                "result": {
                    "ticker": "BHP",
                    "since_hours": 24,
                    "alerts": [],
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "BHP alerts"
    assert sources[0]["source_id"] == "watchlist_alerts:BHP"


def test_agent_format_tv_screener() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "tv_screener",
                "result": {
                    "market": "australia",
                    "results": [
                        {
                            "symbol": "ASX:BHP",
                            "change_percent": 2.1,
                            "close": 45.7,
                            "volume": 1234567,
                        }
                    ],
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "ASX:BHP (AUSTRALIA)"
    assert sources[0]["source_id"] == "tv_screener:AUSTRALIA:ASX:BHP"
    assert "change percent: 2.1" in str(sources[0]["snippet"]).lower()


def test_agent_format_tv_screener_without_rows_still_emits_source_item() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "tv_screener",
                "result": {
                    "market": "australia",
                    "count": 0,
                    "results": [],
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "TradingView screener (AUSTRALIA)"
    assert sources[0]["source_id"] == "tv_screener:AUSTRALIA"


def test_agent_format_get_tv_indicators() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_tv_indicators",
                "result": {
                    "ticker": "BHP",
                    "exchange": "ASX",
                    "indicators": {
                        "RSI": 58.4,
                        "MACD": {"error": "unavailable"},
                    },
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "ASX:BHP indicators"
    assert sources[0]["source_id"] == "tv_indicators:ASX:BHP"
    assert "rsi: 58.4" in str(sources[0]["snippet"]).lower()


def test_agent_format_search_news_truncated_legacy_data_payload() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "search_news",
                "result": {
                    "tool": "search_news",
                    "ok": True,
                    "_truncated": True,
                    "_original_chars": 2500,
                    "data": (
                        '{"tool":"search_news","ok":true,"hits":'
                        '[{"title":"Legacy parsed item","url":"https://example.com/legacy",'
                        '"published_at":"2026-04-20","snippet":"Legacy snippet"}]}'
                    ),
                },
            }
        ]
    )

    assert len(sources) == 1
    assert sources[0]["title"] == "Legacy parsed item"
    assert sources[0]["url"] == "https://example.com/legacy"


def test_agent_format_get_company_dump_source_rows() -> None:
    sources = _build_ui_sources(
        [
            {
                "tool": "get_company_dump",
                "result": {
                    "ticker": "EOS",
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
                            "document_id": "doc-overview",
                            "excerpt": "EOS describes defence and space systems operations.",
                        }
                    ],
                    "announcement_context": [
                        {
                            "title": "Contract announcement",
                            "source_url": "https://example.com/eos-contract.pdf",
                            "document_id": "doc-ann",
                            "text": "Remote weapon systems demand was discussed.",
                        }
                    ],
                    "financials": [
                        {
                            "ticker": "EOS",
                            "period_type": "annual",
                            "period_end": "2025-12-31",
                            "source_document_id": "doc-fin",
                            "revenue": 123,
                        }
                    ],
                },
            }
        ]
    )

    titles = {source["title"] for source in sources}
    assert "EOS annual report" in titles
    assert "Business overview" in titles
    assert "Contract announcement" in titles
    assert "EOS annual 2025-12-31" in titles


def test_local_context_price_and_news_no_hit_sources() -> None:
    sources = _build_ui_sources(
        [
            {
                "type": "local_context",
                "details": {
                    "ticker": "GNC",
                    "price": {
                        "symbol": "GNC.AX",
                        "current": {
                            "price": 6.155,
                            "previous_close": 6.14,
                            "change_percent": 0.24,
                        },
                    },
                    "qual_context_news": {"hits": []},
                },
            }
        ]
    )

    source_ids = {source["source_id"] for source in sources}
    assert "local_price:GNC:current:1d" in source_ids
    assert "search_news:no_hits:gnc" in source_ids
