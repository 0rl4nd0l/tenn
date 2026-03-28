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
    assert SourcesFormatter.format_footer({"dossier_count": 0, "strategy_criteria_count": 0}) == ""


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
