"""Alert reader for watchlist scan results.

Reads alerts written by the background watchlist_research_scan Celery task.
Alerts are stored as JSONL at ~/.tenn/memory/alerts/pending.jsonl.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".tenn" / "memory" / "alerts" / "pending.jsonl"


class AlertReader:
    """Reads and manages watchlist scan alerts."""

    def __init__(self, *, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        *,
        since_hours: int = 24,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """Get recent alerts, optionally filtered by ticker.

        Returns:
            {"ok": bool, "alerts": [...], "total": int}
        """
        if not self._path.exists():
            return {"ok": True, "alerts": [], "total": 0}

        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        cutoff_iso = cutoff.isoformat()

        alerts: list[dict[str, Any]] = []
        for line in self._path.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                alert = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Filter by time.
            if alert.get("ts", "") < cutoff_iso:
                continue

            # Filter by ticker.
            if ticker and alert.get("ticker", "").upper() != ticker.upper():
                continue

            alerts.append(alert)

        # Most recent first.
        alerts.sort(key=lambda a: a.get("ts", ""), reverse=True)
        return {"ok": True, "alerts": alerts, "total": len(alerts)}

    def mark_seen(self, alert_ids: list[str]) -> int:
        """Mark alerts as seen by ID. Returns count of alerts marked."""
        if not self._path.exists() or not alert_ids:
            return 0

        ids_set = set(alert_ids)
        lines = self._path.read_text(encoding="utf-8").splitlines()
        updated = 0
        new_lines: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                alert = json.loads(line)
                if alert.get("id") in ids_set:
                    alert["seen"] = True
                    updated += 1
                new_lines.append(json.dumps(alert, ensure_ascii=False))
            except json.JSONDecodeError:
                new_lines.append(line)

        self._path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return updated

    @staticmethod
    def write_alert(
        *,
        path: Path | str | None = None,
        ticker: str,
        alert_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Write an alert (called by the background scanner task)."""
        import uuid

        target = Path(path) if path else _DEFAULT_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        alert = {
            "id": uuid.uuid4().hex[:12],
            "ticker": ticker.upper(),
            "type": alert_type,
            "message": message,
            "data": data or {},
            "ts": datetime.now(timezone.utc).isoformat(),
            "seen": False,
        }
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
