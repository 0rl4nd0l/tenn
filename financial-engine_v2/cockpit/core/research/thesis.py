"""Thesis tracking service — structured investment theses with evidence links.

Stores theses as JSONL at ~/.tenn/memory/theses/<TICKER>.jsonl.
Each thesis has a signal (BUY→SELL), evidence chain, and risk assessment.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path.home() / ".tenn" / "memory" / "theses"

VALID_SIGNALS = ("BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL")
VALID_STATUSES = ("active", "invalidated", "confirmed", "expired")
VALID_TYPES = ("bull", "bear", "neutral")


class ThesisService:
    """JSONL-backed per-ticker thesis management."""

    def __init__(self, *, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else _DEFAULT_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        ticker: str,
        thesis_statement: str,
        *,
        signal: str = "HOLD",
        thesis_type: str = "neutral",
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Create a new thesis for a ticker."""
        ticker = ticker.strip().upper()
        signal = signal.strip().upper()
        thesis_type = thesis_type.strip().lower()

        if signal not in VALID_SIGNALS:
            return {"ok": False, "error": f"Invalid signal: {signal}. Use: {VALID_SIGNALS}"}
        if thesis_type not in VALID_TYPES:
            thesis_type = "neutral"

        now = datetime.now(timezone.utc).isoformat()
        thesis = {
            "id": uuid.uuid4().hex[:12],
            "ticker": ticker,
            "thesis_statement": thesis_statement.strip(),
            "thesis_type": thesis_type,
            "status": "active",
            "signal": signal,
            "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
            "supporting_evidence": [],
            "disconfirming_evidence": [],
            "risk_assessment": None,
            "created_at": now,
            "updated_at": now,
        }

        self._append(ticker, thesis)
        logger.info("thesis: created %s thesis for %s (signal=%s)", thesis_type, ticker, signal)
        return {"ok": True, "thesis": thesis}

    def add_evidence(
        self,
        ticker: str,
        finding: str,
        *,
        is_supporting: bool = True,
    ) -> dict[str, Any]:
        """Add evidence to the most recent active thesis for a ticker."""
        ticker = ticker.strip().upper()
        theses = self._load_all(ticker)
        active = [t for t in theses if t.get("status") == "active"]
        if not active:
            return {"ok": False, "error": f"No active thesis for {ticker}"}

        target = active[-1]
        evidence_entry = {"text": finding.strip(), "ts": datetime.now(timezone.utc).isoformat()}
        key = "supporting_evidence" if is_supporting else "disconfirming_evidence"
        target[key].append(evidence_entry)
        target["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._rewrite(ticker, theses)
        label = "supporting" if is_supporting else "disconfirming"
        logger.info("thesis: added %s evidence for %s", label, ticker)
        result: dict[str, Any] = {
            "ok": True,
            "ticker": ticker,
            "thesis_id": target["id"],
            "evidence_type": label,
            "total_supporting": len(target["supporting_evidence"]),
            "total_disconfirming": len(target["disconfirming_evidence"]),
        }

        # Auto-evaluate after disconfirming evidence is added.
        if not is_supporting:
            try:
                eval_result = self.auto_evaluate(ticker)
                if eval_result.get("status_changed"):
                    result["auto_invalidated"] = True
                    result["invalidation_reason"] = eval_result.get("reason", "")
                    logger.info(
                        "thesis: auto-invalidated %s thesis %s",
                        ticker, target["id"],
                    )
            except Exception as exc:
                logger.warning("thesis: auto_evaluate failed for %s: %s", ticker, exc)

        return result

    def auto_evaluate(self, ticker: str) -> dict[str, Any]:
        """Evaluate the active thesis evidence ratio and auto-invalidate if warranted.

        Invalidation triggers:
        - Disconfirming > supporting by ratio of 2:1
        - Disconfirming count >= 3 with 0 supporting
        """
        ticker = ticker.strip().upper()
        theses = self._load_all(ticker)
        active = [t for t in theses if t.get("status") == "active"]
        if not active:
            return {"ok": False, "error": f"No active thesis for {ticker}", "status_changed": False}

        target = active[-1]
        supporting = len(target.get("supporting_evidence", []))
        disconfirming = len(target.get("disconfirming_evidence", []))

        should_invalidate = False
        reason = ""

        if disconfirming >= 3 and supporting == 0:
            should_invalidate = True
            reason = (
                f"Auto-invalidated: disconfirming evidence outweighs supporting "
                f"({disconfirming} vs {supporting})"
            )
        elif supporting > 0 and disconfirming >= 2 * supporting:
            should_invalidate = True
            reason = (
                f"Auto-invalidated: disconfirming evidence outweighs supporting "
                f"({disconfirming} vs {supporting})"
            )

        if should_invalidate:
            target["status"] = "invalidated"
            target["invalidation_reason"] = reason
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._rewrite(ticker, theses)
            logger.info("thesis: auto-evaluated %s — invalidated (D:%d vs S:%d)", ticker, disconfirming, supporting)
            return {
                "ok": True,
                "ticker": ticker,
                "thesis_id": target["id"],
                "status_changed": True,
                "new_status": "invalidated",
                "reason": reason,
                "supporting": supporting,
                "disconfirming": disconfirming,
            }

        return {
            "ok": True,
            "ticker": ticker,
            "thesis_id": target["id"],
            "status_changed": False,
            "supporting": supporting,
            "disconfirming": disconfirming,
        }

    def expire_stale(self, days: int = 90) -> dict[str, Any]:
        """Mark active theses older than *days* as expired.

        Scans all ticker files and expires stale theses. Callable from
        the watchlist scanner to keep the thesis store clean.
        """
        now = datetime.now(timezone.utc)
        expired_count = 0
        tickers_affected: list[str] = []

        for path in sorted(self._root.glob("*.jsonl")):
            ticker = path.stem.upper()
            theses = self._load_all(ticker)
            changed = False
            for t in theses:
                if t.get("status") != "active":
                    continue
                created = t.get("created_at", "")
                try:
                    created_dt = datetime.fromisoformat(created)
                except (ValueError, TypeError):
                    continue
                age_days = (now - created_dt).days
                if age_days >= days:
                    t["status"] = "expired"
                    t["invalidation_reason"] = f"Auto-expired: thesis was active for {age_days} days (threshold: {days})"
                    t["updated_at"] = now.isoformat()
                    expired_count += 1
                    changed = True
            if changed:
                self._rewrite(ticker, theses)
                tickers_affected.append(ticker)

        if expired_count:
            logger.info("thesis: expired %d stale theses across %s", expired_count, tickers_affected)

        return {
            "ok": True,
            "expired_count": expired_count,
            "tickers_affected": tickers_affected,
        }

    def get_active(self, ticker: str) -> list[dict[str, Any]]:
        """Return all active theses for a ticker."""
        return [t for t in self._load_all(ticker.strip().upper()) if t.get("status") == "active"]

    def set_risk_assessment(self, ticker: str, thesis_id: str, assessment: dict[str, Any]) -> None:
        """Attach a risk gate assessment to a thesis."""
        ticker = ticker.strip().upper()
        theses = self._load_all(ticker)
        for t in theses:
            if t.get("id") == thesis_id:
                t["risk_assessment"] = assessment
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._rewrite(ticker, theses)
                return

    def invalidate(self, ticker: str, thesis_id: str, *, reason: str = "") -> dict[str, Any]:
        """Mark a thesis as invalidated."""
        ticker = ticker.strip().upper()
        theses = self._load_all(ticker)
        for t in theses:
            if t.get("id") == thesis_id:
                t["status"] = "invalidated"
                t["invalidation_reason"] = reason
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._rewrite(ticker, theses)
                return {"ok": True, "thesis_id": thesis_id, "status": "invalidated"}
        return {"ok": False, "error": f"Thesis {thesis_id} not found"}

    # Persistence helpers.

    def _ticker_path(self, ticker: str) -> Path:
        return self._root / f"{ticker.upper()}.jsonl"

    def _load_all(self, ticker: str) -> list[dict[str, Any]]:
        path = self._ticker_path(ticker)
        if not path.exists():
            return []
        results: list[dict[str, Any]] = []
        for line in path.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return results

    def _append(self, ticker: str, thesis: dict[str, Any]) -> None:
        with self._ticker_path(ticker).open("a", encoding="utf-8") as f:
            f.write(json.dumps(thesis, ensure_ascii=False) + "\n")

    def _rewrite(self, ticker: str, theses: list[dict[str, Any]]) -> None:
        with self._ticker_path(ticker).open("w", encoding="utf-8") as f:
            for t in theses:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
