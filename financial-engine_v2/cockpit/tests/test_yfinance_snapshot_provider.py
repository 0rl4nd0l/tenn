"""Tests for cockpit.core.yfinance_snapshot_provider.

All yfinance calls are mocked — no real network traffic. These tests are
safe to run alongside live extraction (no GPU, no LLM).
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from cockpit.core.significance_score import TickerSnapshot
from cockpit.core.yfinance_snapshot_provider import YFinanceSnapshotProvider


def _fake_history_df(closes: list[float], volume: int = 1_500_000):
    """Build a minimal pandas-like object emulating yfinance's history DataFrame."""

    class _Row:
        def __init__(self, close: float, vol: int) -> None:
            self._data = {"Close": close, "Volume": vol}

        def __getitem__(self, key):
            return self._data[key]

    class _ILoc:
        def __init__(self, rows):
            self._rows = rows

        def __getitem__(self, idx):
            return self._rows[idx]

    rows = [_Row(c, volume) for c in closes]

    class _DF:
        def __init__(self, rows):
            self._rows = rows
            self.empty = len(rows) == 0
            self.iloc = _ILoc(rows)

        def __len__(self):
            return len(self._rows)

    return _DF(rows)


def _install_fake_yfinance(history_result) -> types.ModuleType:
    """Inject a fake `yfinance` module into sys.modules. Returns the module."""
    fake = types.ModuleType("yfinance")
    fake.Ticker = MagicMock()
    fake.Ticker.return_value.history = MagicMock(return_value=history_result)
    sys.modules["yfinance"] = fake
    return fake


@pytest.fixture(autouse=True)
def _reset_yfinance():
    saved = sys.modules.pop("yfinance", None)
    yield
    if saved is not None:
        sys.modules["yfinance"] = saved
    else:
        sys.modules.pop("yfinance", None)


class TestImportFailure:
    def test_returns_none_when_yfinance_unavailable(self) -> None:
        # Force ImportError by leaving yfinance out of sys.modules and
        # patching __import__ to fail.
        provider = YFinanceSnapshotProvider()
        with patch.dict(sys.modules, {"yfinance": None}):
            result = provider("BHP")
        assert result is None


class TestHappyPath:
    def test_two_bar_history_computes_pct_change(self) -> None:
        _install_fake_yfinance(_fake_history_df([100.0, 105.0]))
        provider = YFinanceSnapshotProvider()
        snap = provider("BHP")
        assert snap is not None
        assert isinstance(snap, TickerSnapshot)
        assert snap.ticker == "BHP"
        assert snap.price == pytest.approx(105.0)
        assert snap.pct_change == pytest.approx(5.0)
        assert snap.volume == 1_500_000

    def test_uses_ax_suffix_for_yahoo(self) -> None:
        fake = _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        provider = YFinanceSnapshotProvider()
        provider("BHP")
        fake.Ticker.assert_called_once_with("BHP.AX")

    def test_custom_suffix(self) -> None:
        fake = _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        provider = YFinanceSnapshotProvider(ticker_suffix=".L")
        provider("VOD")
        fake.Ticker.assert_called_once_with("VOD.L")

    def test_ticker_uppercased_in_result(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        provider = YFinanceSnapshotProvider()
        snap = provider("bhp")
        assert snap is not None
        assert snap.ticker == "BHP"


class TestEdgeCases:
    def test_empty_history_returns_none(self) -> None:
        _install_fake_yfinance(_fake_history_df([]))
        provider = YFinanceSnapshotProvider()
        assert provider("BHP") is None

    def test_single_bar_no_pct_change(self) -> None:
        _install_fake_yfinance(_fake_history_df([42.5]))
        provider = YFinanceSnapshotProvider()
        snap = provider("BHP")
        assert snap is not None
        assert snap.price == pytest.approx(42.5)
        assert snap.pct_change is None

    def test_zero_previous_close_yields_none_pct(self) -> None:
        _install_fake_yfinance(_fake_history_df([0.0, 1.0]))
        provider = YFinanceSnapshotProvider()
        snap = provider("BHP")
        assert snap is not None
        assert snap.pct_change is None  # avoids div-by-zero

    def test_yfinance_exception_returns_none(self) -> None:
        fake = types.ModuleType("yfinance")
        fake.Ticker = MagicMock(side_effect=RuntimeError("network down"))
        sys.modules["yfinance"] = fake
        provider = YFinanceSnapshotProvider()
        assert provider("BHP") is None

    def test_zero_volume_recorded_as_none(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0], volume=0))
        provider = YFinanceSnapshotProvider()
        snap = provider("BHP")
        assert snap is not None
        assert snap.volume is None  # falsy volumes treated as missing


class TestEnrichmentHooks:
    def test_news_count_provider_invoked(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        news_provider = MagicMock(return_value=7)
        provider = YFinanceSnapshotProvider(news_count_provider=news_provider)
        snap = provider("BHP")
        assert snap is not None
        assert snap.news_count_24h == 7
        news_provider.assert_called_once_with("BHP")

    def test_alerts_provider_invoked(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        alerts_provider = MagicMock(return_value=True)
        provider = YFinanceSnapshotProvider(alerts_provider=alerts_provider)
        snap = provider("BHP")
        assert snap is not None
        assert snap.has_alerts is True
        alerts_provider.assert_called_once_with("BHP")

    def test_freshness_tracker_invoked(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        tracker = MagicMock()
        tracker.is_stale.return_value = True
        provider = YFinanceSnapshotProvider(freshness_tracker=tracker)
        snap = provider("BHP")
        assert snap is not None
        assert snap.stale_news is True
        tracker.is_stale.assert_called_once_with("BHP")

    def test_enrichment_failure_does_not_kill_snapshot(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        bad_news = MagicMock(side_effect=RuntimeError("news db down"))
        provider = YFinanceSnapshotProvider(news_count_provider=bad_news)
        snap = provider("BHP")
        # Snapshot still returned with default news_count=0
        assert snap is not None
        assert snap.news_count_24h == 0

    def test_no_enrichment_uses_safe_defaults(self) -> None:
        _install_fake_yfinance(_fake_history_df([10.0, 11.0]))
        provider = YFinanceSnapshotProvider()
        snap = provider("BHP")
        assert snap is not None
        assert snap.news_count_24h == 0
        assert snap.has_alerts is False
        assert snap.stale_news is False
