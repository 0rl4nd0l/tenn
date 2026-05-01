"""Tests for cockpit.core.market_update_orchestrator (P5).

All dependencies are mocked — no backend calls, no LLM calls, no GPU work.
Live extraction must continue undisturbed during these tests.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cockpit.core.market_update_orchestrator import (
    MarketUpdateOrchestrator,
    RunResult,
)
from cockpit.core.significance_score import TickerScore, TickerSnapshot


def _fixed_clock() -> datetime:
    return datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)


def _snap(ticker: str, pct_change: float | None = 0.0, **kw) -> TickerSnapshot:
    return TickerSnapshot(
        ticker=ticker,
        price=kw.get("price", 10.0),
        pct_change=pct_change,
        volume=kw.get("volume", 100_000),
        news_count_24h=kw.get("news_count_24h", 0),
        has_alerts=kw.get("has_alerts", False),
        stale_news=kw.get("stale_news", False),
    )


def _make_store() -> MagicMock:
    store = MagicMock()
    store.list_watch_tickers.return_value = []
    store.save_market_update_report.return_value = "report-uuid-1"
    store.add_market_update_followup.side_effect = [
        f"followup-uuid-{i}" for i in range(10)
    ]
    return store


class TestRunTypeValidation:
    def test_invalid_run_type_raises(self) -> None:
        orc = MarketUpdateOrchestrator(
            state_store=_make_store(),
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        with pytest.raises(ValueError, match="run_type"):
            orc.run("weekly", tickers=["BHP"])

    @pytest.mark.parametrize("run_type", ["noon", "final", "manual"])
    def test_valid_run_types_accepted(self, run_type: str) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t, pct_change=1.0),
            clock=_fixed_clock,
        )
        result = orc.run(run_type, tickers=["BHP"])
        assert result.run_type == run_type
        assert result.status in {"complete", "partial"}


class TestEmptyTickerList:
    def test_empty_explicit_list_skips(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=[])
        assert result.status == "skipped"
        assert result.gathered_tickers == 0
        assert result.report_id is None
        store.save_market_update_report.assert_not_called()
        store.add_market_update_followup.assert_not_called()

    def test_no_watchlist_skips(self) -> None:
        store = _make_store()
        store.list_watch_tickers.return_value = []
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        result = orc.run("manual")
        assert result.status == "skipped"
        assert result.report_id is None
        store.save_market_update_report.assert_not_called()

    def test_final_no_watchlist_uses_market_universe_fallback(self) -> None:
        store = _make_store()
        store.list_watch_tickers.return_value = []
        seen: list[str] = []

        def provider(t: str) -> TickerSnapshot | None:
            seen.append(t)
            return _snap(t, pct_change=1.0)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            market_universe_loader=lambda: ["BHP", "RIO"],
            clock=_fixed_clock,
        )
        result = orc.run("final")
        assert result.status == "complete"
        assert result.gathered_tickers == 2
        assert seen == ["BHP", "RIO"]
        store.save_market_update_report.assert_called_once()

    def test_noon_no_watchlist_still_skips_even_with_market_universe_loader(self) -> None:
        store = _make_store()
        store.list_watch_tickers.return_value = []
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            market_universe_loader=lambda: ["BHP", "RIO"],
            clock=_fixed_clock,
        )
        result = orc.run("noon")
        assert result.status == "skipped"
        assert result.report_id is None
        store.save_market_update_report.assert_not_called()


class TestWatchlistResolution:
    def test_falls_back_to_watchlist_when_tickers_is_none(self) -> None:
        store = _make_store()
        store.list_watch_tickers.return_value = [
            {"ticker": "BHP"},
            {"ticker": "RIO"},
        ]
        seen: list[str] = []

        def provider(t: str) -> TickerSnapshot | None:
            seen.append(t)
            return _snap(t)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            clock=_fixed_clock,
        )
        result = orc.run("noon")
        assert sorted(seen) == ["BHP", "RIO"]
        assert result.gathered_tickers == 2

    def test_tickers_uppercased(self) -> None:
        store = _make_store()
        seen: list[str] = []

        def provider(t: str) -> TickerSnapshot | None:
            seen.append(t)
            return _snap(t)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            clock=_fixed_clock,
        )
        orc.run("manual", tickers=["bhp", "rio"])
        assert seen == ["BHP", "RIO"]


class TestHappyPath:
    def test_gather_score_persist_for_each_ticker(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t, pct_change=3.0),
            clock=_fixed_clock,
        )
        result = orc.run("noon", tickers=["BHP", "RIO"])

        assert result.status == "complete"
        assert result.gathered_tickers == 2
        assert result.report_id == "report-uuid-1"

        store.save_market_update_report.assert_called_once()
        kwargs = store.save_market_update_report.call_args.kwargs
        assert kwargs["run_type"] == "noon"
        assert kwargs["status"] == "complete"
        assert kwargs["report_date"] == "2026-04-20"

        summary = kwargs["summary"]
        assert summary["run_type"] == "noon"
        tickers_in_summary = {t["ticker"] for t in summary["tickers"]}
        assert tickers_in_summary == {"BHP", "RIO"}

    def test_summary_includes_significance_and_reasons(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t, pct_change=6.0),
            clock=_fixed_clock,
        )
        orc.run("manual", tickers=["BHP"])

        summary = store.save_market_update_report.call_args.kwargs["summary"]
        entry = summary["tickers"][0]
        assert entry["ticker"] == "BHP"
        assert entry["significance"] >= 0.5
        assert any("major" in r.lower() for r in entry["reasons"])
        assert entry["pct_change"] == 6.0

    def test_headline_template_is_deterministic(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(
                t, pct_change=6.0, has_alerts=True
            ),
            clock=_fixed_clock,
        )
        orc.run("manual", tickers=["BHP", "RIO"])
        summary = store.save_market_update_report.call_args.kwargs["summary"]
        assert "headline" in summary
        assert isinstance(summary["headline"], str)
        # Template-based, not LLM-generated: no surprises in content
        assert "manual" in summary["headline"].lower()

    def test_large_scan_uses_bounded_parallel_snapshotting(self) -> None:
        store = _make_store()
        active = 0
        max_active = 0
        lock = threading.Lock()

        def provider(t: str) -> TickerSnapshot | None:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            try:
                time.sleep(0.01)
                return _snap(t, pct_change=1.0)
            finally:
                with lock:
                    active -= 1

        tickers = [f"T{i:02d}" for i in range(20)]
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            max_snapshot_workers=4,
            parallel_snapshot_threshold=5,
            clock=_fixed_clock,
        )

        result = orc.run("final", tickers=tickers)

        assert result.status == "complete"
        assert max_active > 1
        assert max_active <= 4
        summary = store.save_market_update_report.call_args.kwargs["summary"]
        assert [row["ticker"] for row in summary["tickers"]] == tickers

    def test_large_parallel_scan_keeps_per_ticker_failure_contract(self) -> None:
        store = _make_store()

        def provider(t: str) -> TickerSnapshot | None:
            if t == "T02":
                raise RuntimeError("upstream died")
            if t == "T03":
                return None
            return _snap(t, pct_change=1.0)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            max_snapshot_workers=3,
            parallel_snapshot_threshold=2,
            clock=_fixed_clock,
        )

        result = orc.run("final", tickers=["T01", "T02", "T03", "T04"])

        assert result.status == "partial"
        assert result.gathered_tickers == 2
        assert any("T02: snapshot failed: upstream died" in e for e in result.errors)
        assert any("T03: no snapshot available" in e for e in result.errors)
        summary = store.save_market_update_report.call_args.kwargs["summary"]
        assert [row["ticker"] for row in summary["tickers"]] == ["T01", "T04"]


class TestFollowupQueueing:
    def test_high_significance_ticker_queued(self) -> None:
        store = _make_store()

        def provider(t: str) -> TickerSnapshot | None:
            # BHP significant, RIO not
            if t == "BHP":
                return _snap(t, pct_change=6.0, has_alerts=True)
            return _snap(t, pct_change=0.5)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            followup_threshold=0.5,
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP", "RIO"])

        assert result.queued_followups == 1
        assert store.add_market_update_followup.call_count == 1
        call_kwargs = store.add_market_update_followup.call_args.kwargs
        assert call_kwargs["ticker"] == "BHP"
        assert call_kwargs["report_id"] == "report-uuid-1"
        assert call_kwargs["action_type"] == "review"
        assert call_kwargs["priority_score"] >= 0.5
        assert "reasons" in call_kwargs["reason"]

    def test_threshold_respected(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t, pct_change=2.5),
            followup_threshold=0.5,  # notable move = 0.3, below threshold
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        assert result.queued_followups == 0
        store.add_market_update_followup.assert_not_called()

    def test_custom_threshold(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t, pct_change=2.5),
            followup_threshold=0.1,  # lenient: 0.3 clears it
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        assert result.queued_followups == 1


class TestErrorHandling:
    def test_provider_none_is_recorded_but_non_fatal(self) -> None:
        store = _make_store()

        def provider(t: str) -> TickerSnapshot | None:
            return None if t == "RIO" else _snap(t, pct_change=3.0)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP", "RIO"])
        assert result.status == "partial"
        assert result.gathered_tickers == 1
        assert any("RIO" in e for e in result.errors)
        store.save_market_update_report.assert_called_once()

    def test_provider_exception_is_captured(self) -> None:
        store = _make_store()

        def provider(t: str) -> TickerSnapshot | None:
            if t == "RIO":
                raise RuntimeError("upstream died")
            return _snap(t, pct_change=3.0)

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP", "RIO"])
        assert result.status == "partial"
        assert result.gathered_tickers == 1
        assert any("RIO" in e for e in result.errors)
        assert any("upstream died" in e for e in result.errors)

    def test_all_providers_fail_marks_failed(self) -> None:
        store = _make_store()

        def provider(t: str) -> TickerSnapshot | None:
            raise RuntimeError("all gone")

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=provider,
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP", "RIO"])
        assert result.status == "failed"
        assert result.gathered_tickers == 0
        # Even failed runs persist a report so operators can inspect errors
        store.save_market_update_report.assert_called_once()
        saved_status = store.save_market_update_report.call_args.kwargs["status"]
        assert saved_status == "failed"


class TestResultShape:
    def test_run_result_is_frozen(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        assert isinstance(result, RunResult)
        with pytest.raises((AttributeError, Exception)):
            result.status = "hacked"  # type: ignore[misc]

    def test_timestamps_are_isoformat(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        # Deterministic clock -> deterministic timestamps
        assert result.started_at == "2026-04-20T12:00:00+00:00"
        assert result.finished_at == "2026-04-20T12:00:00+00:00"

    def test_errors_is_tuple(self) -> None:
        store = _make_store()
        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        assert isinstance(result.errors, tuple)


class TestCustomScorer:
    def test_injected_scorer_is_used(self) -> None:
        store = _make_store()

        def always_critical(snap: TickerSnapshot) -> TickerScore:
            return TickerScore(
                ticker=snap.ticker,
                significance=0.99,
                reasons=("custom-rule",),
            )

        orc = MarketUpdateOrchestrator(
            state_store=store,
            snapshot_provider=lambda t: _snap(t),
            scorer=always_critical,
            followup_threshold=0.5,
            clock=_fixed_clock,
        )
        result = orc.run("manual", tickers=["BHP"])
        assert result.queued_followups == 1
        reason = store.add_market_update_followup.call_args.kwargs["reason"]
        assert "custom-rule" in reason["reasons"]
