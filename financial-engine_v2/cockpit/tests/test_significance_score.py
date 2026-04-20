"""Tests for cockpit.core.significance_score (P5).

Pure-function scorer for verbal market-update prioritisation.
No I/O, no LLM, no GPU. Fast unit tests only.
"""

from __future__ import annotations

import pytest

from cockpit.core.significance_score import (
    TickerScore,
    TickerSnapshot,
    compute_significance,
)


@pytest.mark.unit
class TestTickerSnapshot:
    def test_snapshot_is_frozen(self) -> None:
        snap = TickerSnapshot(
            ticker="BHP", price=42.10, pct_change=1.2, volume=1_000_000
        )
        with pytest.raises((AttributeError, Exception)):
            snap.ticker = "RIO"  # type: ignore[misc]

    def test_snapshot_defaults(self) -> None:
        snap = TickerSnapshot(
            ticker="BHP", price=None, pct_change=None, volume=None
        )
        assert snap.news_count_24h == 0
        assert snap.has_alerts is False
        assert snap.stale_news is False


@pytest.mark.unit
class TestComputeSignificance:
    def _snap(self, **overrides) -> TickerSnapshot:
        base = dict(
            ticker="BHP",
            price=42.10,
            pct_change=0.0,
            volume=100_000,
            news_count_24h=0,
            has_alerts=False,
            stale_news=False,
        )
        base.update(overrides)
        return TickerSnapshot(**base)  # type: ignore[arg-type]

    def test_zero_baseline_has_no_significance(self) -> None:
        score = compute_significance(self._snap())
        assert score.significance == pytest.approx(0.0)
        assert score.reasons == ()
        assert score.ticker == "BHP"

    def test_returns_ticker_score_dataclass(self) -> None:
        score = compute_significance(self._snap())
        assert isinstance(score, TickerScore)

    def test_ticker_is_uppercased(self) -> None:
        score = compute_significance(self._snap(ticker="bhp"))
        assert score.ticker == "BHP"

    def test_major_move_positive(self) -> None:
        score = compute_significance(self._snap(pct_change=5.5))
        assert score.significance == pytest.approx(0.5)
        assert any("major" in r.lower() for r in score.reasons)

    def test_major_move_negative_uses_magnitude(self) -> None:
        score = compute_significance(self._snap(pct_change=-7.0))
        assert score.significance == pytest.approx(0.5)
        assert any("major" in r.lower() for r in score.reasons)

    def test_notable_move_threshold(self) -> None:
        score = compute_significance(self._snap(pct_change=2.0))
        assert score.significance == pytest.approx(0.3)
        assert any("notable" in r.lower() for r in score.reasons)

    def test_small_move_no_bonus(self) -> None:
        score = compute_significance(self._snap(pct_change=1.5))
        assert score.significance == pytest.approx(0.0)
        assert score.reasons == ()

    def test_has_alerts_adds_score(self) -> None:
        score = compute_significance(self._snap(has_alerts=True))
        assert score.significance == pytest.approx(0.3)
        assert any("alert" in r.lower() for r in score.reasons)

    def test_high_news_volume_adds_score(self) -> None:
        score = compute_significance(self._snap(news_count_24h=5))
        assert score.significance == pytest.approx(0.2)
        assert any("news" in r.lower() for r in score.reasons)

    def test_low_news_volume_no_bonus(self) -> None:
        score = compute_significance(self._snap(news_count_24h=2))
        assert score.significance == pytest.approx(0.0)

    def test_capped_at_one(self) -> None:
        score = compute_significance(
            self._snap(
                pct_change=10.0,
                has_alerts=True,
                news_count_24h=20,
            )
        )
        assert score.significance == pytest.approx(1.0)
        # All three reasons captured, even when capped
        assert any("major" in r.lower() for r in score.reasons)
        assert any("alert" in r.lower() for r in score.reasons)
        assert any("news" in r.lower() for r in score.reasons)

    def test_none_pct_change_handled(self) -> None:
        score = compute_significance(
            self._snap(pct_change=None, has_alerts=True)
        )
        assert score.significance == pytest.approx(0.3)
        # No "move" reason — only the alert reason
        assert not any("move" in r.lower() for r in score.reasons)

    def test_reasons_is_tuple(self) -> None:
        score = compute_significance(self._snap(has_alerts=True))
        assert isinstance(score.reasons, tuple)

    def test_stale_news_records_reason_only(self) -> None:
        # Stale news is informational; it must not by itself bump the score.
        score = compute_significance(self._snap(stale_news=True))
        assert score.significance == pytest.approx(0.0)
        assert any("stale" in r.lower() for r in score.reasons)

    def test_combined_notable_and_alerts(self) -> None:
        score = compute_significance(
            self._snap(pct_change=-3.0, has_alerts=True)
        )
        # 0.3 (notable) + 0.3 (alerts) = 0.6
        assert score.significance == pytest.approx(0.6)
