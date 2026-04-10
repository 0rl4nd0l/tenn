"""Tests that unavailable services return ok=False, not empty results.

Validates the fix for silent degradation in get_watchlist_alerts,
get_thesis, and review_open_decisions — these previously returned
{ok: true, data: []} when backing services were None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cockpit.core.tool_executor import ToolExecutor


def _make_executor(**overrides) -> ToolExecutor:
    """Build a ToolExecutor with all optional services as None by default."""
    mock_router = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None

    defaults = {
        "tool_router": mock_router,
        "action_registry": mock_registry,
        "alert_reader": None,
        "thesis_service": None,
        "reflection_service": None,
    }
    defaults.update(overrides)
    return ToolExecutor(**defaults)


class TestWatchlistAlertsDegradation:
    def test_returns_ok_false_when_alert_reader_none(self) -> None:
        executor = _make_executor(alert_reader=None)
        result = executor.execute("get_watchlist_alerts", {})
        assert result["ok"] is False
        assert "error" in result

    def test_returns_ok_true_when_alert_reader_available(self) -> None:
        mock_reader = MagicMock()
        mock_reader.get.return_value = {"ok": True, "alerts": [{"id": 1}]}
        executor = _make_executor(alert_reader=mock_reader)
        result = executor.execute("get_watchlist_alerts", {})
        assert result["ok"] is True


class TestThesisDegradation:
    def test_returns_ok_false_when_thesis_service_none(self) -> None:
        executor = _make_executor(thesis_service=None)
        result = executor.execute("get_thesis", {"ticker": "BHP"})
        assert result["ok"] is False
        assert "error" in result

    def test_returns_ok_true_when_thesis_service_available(self) -> None:
        mock_thesis = MagicMock()
        mock_thesis.get_active.return_value = [{"id": "t1"}]
        executor = _make_executor(thesis_service=mock_thesis)
        result = executor.execute("get_thesis", {"ticker": "BHP"})
        assert result["ok"] is True
        assert result["theses"] == [{"id": "t1"}]


class TestReviewOpenDecisionsDegradation:
    def test_returns_ok_false_when_reflection_service_none(self) -> None:
        executor = _make_executor(reflection_service=None)
        result = executor.execute("review_open_decisions", {})
        assert result["ok"] is False
        assert "error" in result

    def test_returns_ok_true_when_reflection_service_available(self) -> None:
        mock_reflection = MagicMock()
        mock_reflection.review_open_decisions.return_value = [{"id": "d1"}]
        executor = _make_executor(reflection_service=mock_reflection)
        result = executor.execute("review_open_decisions", {})
        assert result["ok"] is True
        assert result["decisions"] == [{"id": "d1"}]


class TestCheckDecisionOutcomeDegradation:
    def test_returns_ok_false_when_reflection_service_none(self) -> None:
        executor = _make_executor(reflection_service=None)
        result = executor.execute("check_decision_outcome", {"ticker": "BHP"})
        assert result["ok"] is False
        assert "error" in result
