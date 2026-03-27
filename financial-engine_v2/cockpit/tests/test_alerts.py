"""Tests for AlertReader (watchlist scan alert reader)."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from cockpit.core.research.alerts import AlertReader


def _write_alert(path, ticker, message, *, hours_ago=0, alert_id="a1"):
    """Helper to write a test alert to the JSONL file."""
    ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    alert = {
        "id": alert_id,
        "ticker": ticker,
        "type": "research_update",
        "message": message,
        "data": {},
        "ts": ts.isoformat(),
        "seen": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


# ------------------------------------------------------------------
# Happy path: get() returns alerts from the last N hours
# ------------------------------------------------------------------


def test_get_recent_alerts(tmp_path):
    """Returns alerts from the last N hours, filters out older ones."""
    alert_path = tmp_path / "pending.jsonl"

    # Recent alert (1 hour ago)
    _write_alert(alert_path, "BHP", "Revenue beat expectations", hours_ago=1, alert_id="r1")
    # Old alert (48 hours ago)
    _write_alert(alert_path, "CSL", "Old news", hours_ago=48, alert_id="r2")

    reader = AlertReader(path=alert_path)
    result = reader.get(since_hours=24)

    assert result["ok"] is True
    assert result["total"] == 1
    assert result["alerts"][0]["ticker"] == "BHP"
    assert result["alerts"][0]["message"] == "Revenue beat expectations"


def test_get_filter_by_ticker(tmp_path):
    """Ticker filter returns only matching alerts."""
    alert_path = tmp_path / "pending.jsonl"
    _write_alert(alert_path, "BHP", "BHP alert", hours_ago=1, alert_id="t1")
    _write_alert(alert_path, "CSL", "CSL alert", hours_ago=1, alert_id="t2")

    reader = AlertReader(path=alert_path)
    result = reader.get(since_hours=24, ticker="CSL")

    assert result["total"] == 1
    assert result["alerts"][0]["ticker"] == "CSL"


# ------------------------------------------------------------------
# Missing file: returns empty list, no raise
# ------------------------------------------------------------------


def test_missing_file_returns_empty(tmp_path):
    """When alert file does not exist, returns empty list."""
    reader = AlertReader(path=tmp_path / "nonexistent" / "pending.jsonl")
    result = reader.get()

    assert result["ok"] is True
    assert result["alerts"] == []
    assert result["total"] == 0


# ------------------------------------------------------------------
# write_alert static method
# ------------------------------------------------------------------


def test_write_alert_creates_file(tmp_path):
    """write_alert creates the alert file and writes valid JSONL."""
    alert_path = tmp_path / "alerts" / "pending.jsonl"
    AlertReader.write_alert(
        path=alert_path,
        ticker="WDS",
        alert_type="price_move",
        message="WDS up 3%",
    )

    assert alert_path.exists()
    lines = alert_path.read_text().strip().split("\n")
    assert len(lines) == 1
    alert = json.loads(lines[0])
    assert alert["ticker"] == "WDS"
    assert alert["message"] == "WDS up 3%"
    assert alert["seen"] is False


def test_get_sorts_most_recent_first(tmp_path):
    """Alerts are returned most-recent-first."""
    alert_path = tmp_path / "pending.jsonl"
    _write_alert(alert_path, "BHP", "Older", hours_ago=5, alert_id="s1")
    _write_alert(alert_path, "BHP", "Newer", hours_ago=1, alert_id="s2")

    reader = AlertReader(path=alert_path)
    result = reader.get(since_hours=24)

    assert result["total"] == 2
    assert result["alerts"][0]["message"] == "Newer"
    assert result["alerts"][1]["message"] == "Older"
