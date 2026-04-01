"""test_prose_shares_extraction.py — Tests for shares_outstanding prose fallback.

Covers:
  - _extract_shares_from_prose regex patterns
  - Pass 4 reconciler integration with prose fallback
  - Sanity range filtering
  - Priority: table extraction wins over prose
"""
from __future__ import annotations

import pytest

from app.services.multipass_extraction import (
    METRIC_FIELDS,
    _extract_shares_from_prose,
    _run_pass4_reconciler,
)


# ---------------------------------------------------------------------------
# _extract_shares_from_prose
# ---------------------------------------------------------------------------


class TestExtractSharesFromProse:
    def test_anz_comprises_pattern(self) -> None:
        """ANZ Note 13: 'comprises 3,003,366,782 fully paid shares'."""
        sections = [
            {"text": "Note 13 Share Capital", "page": 44, "heading": True},
            {
                "text": "The Company share capital comprises 3,003,366,782 "
                "fully paid shares (30 September 2024: 2,994,521,186).",
                "page": 44,
            },
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value == 3_003_366_782.0
        assert "page_44" in prov

    def test_shares_on_issue_pattern(self) -> None:
        """'1,924,937,480 ordinary shares on issue'."""
        sections = [
            {
                "text": "As at 30 June 2024, there were 1,924,937,480 "
                "ordinary shares on issue.",
                "page": 30,
            },
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value == 1_924_937_480.0

    def test_colon_pattern(self) -> None:
        """'Number of shares on issue: 280,874,770'."""
        sections = [
            {
                "text": "Number of shares on issue: 280,874,770",
                "page": 24,
            },
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value == 280_874_770.0

    def test_total_issued_shares_pattern(self) -> None:
        """'total issued shares 1,075,565,246 shares'."""
        sections = [
            {
                "text": "As at period end, the total issued capital of "
                "1,075,565,246 shares remained unchanged.",
                "page": 36,
            },
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value == 1_075_565_246.0

    def test_no_match_returns_none(self) -> None:
        sections = [
            {"text": "Revenue was $5.2 billion.", "page": 1},
            {"text": "Dividends per share: $0.74", "page": 2},
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value is None
        assert prov == ""

    def test_empty_sections(self) -> None:
        value, prov = _extract_shares_from_prose([])
        assert value is None

    def test_rejects_too_small_value(self) -> None:
        """Values < 1M are likely dollar amounts, not share counts."""
        sections = [
            {
                "text": "The company comprises 500 fully paid shares.",
                "page": 10,
            },
        ]
        value, _ = _extract_shares_from_prose(sections)
        assert value is None

    def test_rejects_too_large_value(self) -> None:
        """Values > 100B are implausible for share counts."""
        sections = [
            {
                "text": "comprises 200,000,000,000,000 fully paid shares.",
                "page": 10,
            },
        ]
        value, _ = _extract_shares_from_prose(sections)
        assert value is None

    def test_prefers_note_sections(self) -> None:
        """Sections with 'Note' or 'share capital' are checked first."""
        sections = [
            {"text": "Revenue comprises 5,000,000,000 items.", "page": 1},
            {
                "text": "Note 13: Share Capital comprises 3,003,366,782 "
                "fully paid shares.",
                "page": 44,
            },
        ]
        value, prov = _extract_shares_from_prose(sections)
        assert value == 3_003_366_782.0
        assert "page_44" in prov


# ---------------------------------------------------------------------------
# Pass 4 integration: prose fallback for shares_outstanding
# ---------------------------------------------------------------------------


class TestPass4ProseSharesFallback:
    def _pass1(self) -> dict:
        return {
            "report_type": "H",
            "period_end": "2025-03-31",
            "currency": "AUD",
            "scale": "millions",
        }

    def _pass3b(self) -> dict:
        return {
            "risk_summary": None, "risk_bullets": None,
            "guidance_summary": None, "material_changes": None,
            "confidence_narrative": 0.0,
        }

    def test_prose_fills_null_shares(self) -> None:
        """When table extraction yields null shares, prose fallback fills it."""
        pass3a = [{
            "_source": "income_statement",
            "revenue": 11_153_000_000,
            "ebit": 5_222_000_000,
            "pass3_confidence": 0.9,
        }]
        sections = [
            {
                "text": "Note 13 Share Capital comprises 3,003,366,782 "
                "fully paid shares.",
                "page": 44,
            },
        ]
        result = _run_pass4_reconciler(
            pass3a, self._pass3b(), self._pass1(), sections=sections,
        )
        assert result["metrics"]["shares_outstanding"] == 3_003_366_782.0
        assert "prose_note" in result["provenance"]["shares_outstanding"]

    def test_table_shares_not_overridden(self) -> None:
        """Table-extracted shares_outstanding takes priority over prose."""
        pass3a = [{
            "_source": "share_capital",
            "shares_outstanding": 2_994_521_186,
            "pass3_confidence": 0.85,
        }]
        sections = [
            {
                "text": "Note 13 Share Capital comprises 3,003,366,782 "
                "fully paid shares.",
                "page": 44,
            },
        ]
        result = _run_pass4_reconciler(
            pass3a, self._pass3b(), self._pass1(), sections=sections,
        )
        # Table value wins
        assert result["metrics"]["shares_outstanding"] == 2_994_521_186

    def test_no_sections_no_crash(self) -> None:
        """Sections=None doesn't crash Pass 4."""
        pass3a = [{
            "_source": "income_statement",
            "revenue": 1_000_000,
            "pass3_confidence": 0.8,
        }]
        result = _run_pass4_reconciler(
            pass3a, self._pass3b(), self._pass1(), sections=None,
        )
        assert result["metrics"]["shares_outstanding"] is None
