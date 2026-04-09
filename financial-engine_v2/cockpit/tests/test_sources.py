"""Tests for SourcesFormatter — evidence provenance footer for analysis responses."""

from __future__ import annotations

from cockpit.core.sources import SourcesFormatter


# ------------------------------------------------------------------
# Happy path: RAG hits present
# ------------------------------------------------------------------


def test_format_footer_with_rag_hits():
    sources = {
        "rag_hits": [
            {"title": "BHP 2024 Annual Report", "score": 0.81, "doc_type": "company"},
            {"title": "BHP H1 2024 Results", "score": 0.74, "doc_type": "company"},
            {"title": "BHP Investor Day 2023", "score": 0.71, "doc_type": "company"},
        ],
        "financial_periods": [("BHP", "2024-06-30", "FY"), ("BHP", "2023-06-30", "FY")],
        "dossier_count": 2,
        "strategy_criteria_count": 3,
    }
    footer = SourcesFormatter.format_footer(sources)
    assert "Sources" in footer
    assert "RAG: 3 docs" in footer
    assert "Financial: 2 periods" in footer
    assert "Dossier: 2 findings" in footer
    assert "Strategy: 3 criteria" in footer
    assert "BHP 2024 Annual Report" in footer
    assert "score: 0.81" in footer
    # Separator lines present
    assert "─" in footer


# ------------------------------------------------------------------
# Empty sources — returns empty string
# ------------------------------------------------------------------


def test_format_footer_empty_sources():
    assert SourcesFormatter.format_footer({}) == ""
    assert (
        SourcesFormatter.format_footer(
            {"dossier_count": 0, "strategy_criteria_count": 0}
        )
        == ""
    )


def test_format_footer_merges_multiple_payloads():
    payloads = [
        {
            "rag_hits": [{"title": "Doc A", "score": 0.8}],
            "dossier_count": 1,
        },
        {
            "rag_hits": [{"title": "Doc B", "score": 0.7}],
            "financial_periods": [("BHP", "2024-06-30", "FY")],
            "dossier_count": 2,
        },
    ]
    footer = SourcesFormatter.format_footer(payloads)
    assert "RAG: 2 docs" in footer
    assert "Dossier: 3 findings" in footer
    assert "Financial: 1 period" in footer


# ------------------------------------------------------------------
# show_sources=False — returns empty string
# ------------------------------------------------------------------


def test_format_footer_show_sources_false():
    sources = {
        "rag_hits": [{"title": "BHP Report", "score": 0.81, "doc_type": "annual"}],
        "dossier_count": 1,
    }
    assert SourcesFormatter.format_footer(sources, show_sources=False) == ""


# ------------------------------------------------------------------
# Caps RAG hits at 3
# ------------------------------------------------------------------


def test_format_footer_caps_at_3_rag_hits():
    sources = {
        "rag_hits": [
            {"title": f"Doc {i}", "score": 0.9 - i * 0.1, "doc_type": "company"}
            for i in range(5)
        ],
    }
    footer = SourcesFormatter.format_footer(sources)
    assert "Doc 0" in footer
    assert "Doc 1" in footer
    assert "Doc 2" in footer
    assert "Doc 3" not in footer
    assert "Doc 4" not in footer


# ------------------------------------------------------------------
# Truncates long titles
# ------------------------------------------------------------------


def test_format_footer_truncates_long_titles():
    long_title = "A" * 80
    sources = {
        "rag_hits": [{"title": long_title, "score": 0.5, "doc_type": "company"}],
    }
    footer = SourcesFormatter.format_footer(sources)
    # Title should be truncated — not the full 80 chars
    assert long_title not in footer
    assert "…" in footer


# ------------------------------------------------------------------
# Collect sources from all evidence entries
# ------------------------------------------------------------------


def test_collect_sources_payloads_across_multiple_evidence_entries():
    evidence = [
        {"details": {"sources": {"rag_hits": [{"source_id": "src-1"}]}}},
        {"details": {"sources": {"rag_hits": [{"source_id": "src-2"}]}}},
        {"not_details": {}},
    ]
    payloads = SourcesFormatter.collect_sources_payloads(evidence)
    assert len(payloads) == 2
    assert payloads[0]["rag_hits"][0]["source_id"] == "src-1"
    assert payloads[1]["rag_hits"][0]["source_id"] == "src-2"


def test_collect_sources_payloads_accepts_details_as_source_payload():
    evidence = [
        {
            "details": {
                "rag_hits": [{"source_id": "direct-1", "title": "Direct doc"}],
                "financial_periods": [("BHP", "2024-06-30", "FY")],
            },
        }
    ]
    payloads = SourcesFormatter.collect_sources_payloads(evidence)
    assert len(payloads) == 1
    assert payloads[0]["rag_hits"][0]["source_id"] == "direct-1"


def test_collect_sources_payloads_falls_back_to_result_source_payload():
    evidence = [
        {
            "type": "orchestrator",
            "details": {
                "source_status": {
                    "asx_docs": {
                        "status": "ok",
                        "found": True,
                    }
                }
            },
            "result": {
                "rag_hits": [{"source_id": "result-1", "title": "From result"}],
            },
        }
    ]
    payloads = SourcesFormatter.collect_sources_payloads(evidence)
    assert len(payloads) == 1
    assert payloads[0]["rag_hits"][0]["source_id"] == "result-1"


# ------------------------------------------------------------------
# List formatting for interactive inspection
# ------------------------------------------------------------------


def test_format_list_from_multiple_source_payloads():
    payloads = [
        {"rag_hits": [{"title": "First document", "score": 0.99}]},
        {"rag_hits": [{"title": "Second source", "score": 0.88}]},
    ]
    listing = SourcesFormatter.format_list(payloads)
    assert "Sources list" in listing
    assert "  1. First document" in listing
    assert "  2. Second source" in listing


def test_format_show_from_multiple_source_payloads():
    payloads = [
        {
            "rag_hits": [
                {
                    "title": "First document",
                    "score": 0.99,
                    "doc_type": "company",
                    "source_id": "s1",
                },
                {
                    "title": "Second source",
                    "score": 0.88,
                    "doc_type": "news",
                    "source_id": "s2",
                },
            ]
        }
    ]
    assert "Source 2: Second source" in SourcesFormatter.format_show(payloads, 2)
    assert "doc_type: news" in SourcesFormatter.format_show(payloads, 2)
    assert "Source index out of range. Use 1..2." in SourcesFormatter.format_show(
        payloads, 3
    )


# ------------------------------------------------------------------
# Partial sources — only RAG present, others absent
# ------------------------------------------------------------------


def test_format_footer_partial_sources():
    sources = {
        "rag_hits": [{"title": "BHP Report", "score": 0.65, "doc_type": "news"}],
    }
    footer = SourcesFormatter.format_footer(sources)
    assert "RAG: 1 doc" in footer
    assert "Financial" not in footer
    assert "Dossier" not in footer
    assert "Strategy" not in footer
    assert "BHP Report" in footer
    assert "news" in footer
