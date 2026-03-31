"""Reflection service — learn from strategy decision outcomes.

Records decision context snapshots when signals are assigned, then checks
what happened afterward. Stores (situation, outcome) pairs in SituationMemory
so the system learns from past decisions.

Decision snapshots at ~/.tenn/memory/decisions/<TICKER>_<ts>.json.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path.home() / ".tenn" / "memory" / "decisions"
_REVIEW_THRESHOLD_DAYS = 30


class ReflectionService:
    """Tracks decision outcomes and records lessons to SituationMemory."""

    def __init__(
        self,
        *,
        situation_memory: Any | None = None,
        thesis_service: Any | None = None,
        scorer: Any | None = None,
        tool_router: Any | None = None,
        root: Path | str | None = None,
    ) -> None:
        self._memory = situation_memory
        self._thesis = thesis_service
        self._scorer = scorer
        self._router = tool_router
        self._root = Path(root) if root else _DEFAULT_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    def record_decision_context(
        self,
        ticker: str,
        signal: str,
        *,
        thesis: str = "",
        score_data: dict[str, Any] | None = None,
        risk_assessment: dict[str, Any] | None = None,
    ) -> str:
        """Snapshot the decision context. Returns the decision_id."""
        ticker = ticker.strip().upper()
        now = datetime.now(timezone.utc)
        decision_id = f"{ticker}_{now.strftime('%Y%m%dT%H%M%S')}"

        price_at_decision = None
        if self._router is not None:
            try:
                price_ctx = self._router.get_price_context_for_window(
                    ticker=ticker, range_="1mo", interval="1d", max_history_rows=5,
                )
                price_at_decision = (price_ctx or {}).get("price_state", {}).get("last_close")
            except Exception:
                pass

        snapshot = {
            "decision_id": decision_id,
            "ticker": ticker,
            "signal": signal,
            "thesis": thesis,
            "composite_score": (score_data or {}).get("composite_score"),
            "financial_health": (score_data or {}).get("financial_health"),
            "price_at_decision": price_at_decision,
            "risk_assessment_summary": (risk_assessment or {}).get("judge_synthesis", ""),
            "risk_level": (risk_assessment or {}).get("risk_level", ""),
            "ts": now.isoformat(),
            "reflected": False,
        }

        path = self._root / f"{decision_id}.json"
        path.write_text(json.dumps(snapshot, default=str, indent=2), encoding="utf-8")
        logger.info("reflection: recorded decision %s", decision_id)
        return decision_id

    def check_outcome(self, ticker: str) -> dict[str, Any]:
        """Check what happened since the most recent decision for *ticker*."""
        ticker = ticker.strip().upper()
        snapshot = self._latest_snapshot(ticker)
        if snapshot is None:
            return {"ok": False, "error": f"No decision snapshot found for {ticker}"}

        price_now = None
        if self._router is not None:
            try:
                price_ctx = self._router.get_price_context_for_window(
                    ticker=ticker, range_="1mo", interval="1d", max_history_rows=5,
                )
                price_now = (price_ctx or {}).get("price_state", {}).get("last_close")
            except Exception:
                pass

        score_now = None
        if self._scorer is not None:
            try:
                score_result = self._scorer.score(ticker)
                if score_result.get("ok"):
                    score_now = score_result.get("composite_score")
            except Exception:
                pass

        price_at = snapshot.get("price_at_decision")
        price_change_pct = None
        if price_at and price_now and float(price_at) > 0:
            price_change_pct = round((float(price_now) - float(price_at)) / float(price_at) * 100, 2)

        score_at = snapshot.get("composite_score")
        score_change = None
        if score_at is not None and score_now is not None:
            score_change = round(float(score_now) - float(score_at), 1)

        days_elapsed = 0
        try:
            dt = datetime.fromisoformat(snapshot.get("ts", ""))
            days_elapsed = (datetime.now(timezone.utc) - dt).days
        except Exception:
            pass

        outcome_quality = _assess_outcome(snapshot.get("signal", ""), price_change_pct)

        return {
            "ok": True,
            "decision_id": snapshot.get("decision_id"),
            "ticker": ticker,
            "signal_was": snapshot.get("signal"),
            "thesis": snapshot.get("thesis", ""),
            "price_at_decision": price_at,
            "price_now": price_now,
            "price_change_pct": price_change_pct,
            "score_at_decision": score_at,
            "score_now": score_now,
            "score_change": score_change,
            "days_elapsed": days_elapsed,
            "outcome_quality": outcome_quality,
            "reflected": snapshot.get("reflected", False),
        }

    def reflect_and_learn(self, ticker: str) -> dict[str, Any]:
        """Check outcome and record the lesson to SituationMemory."""
        outcome = self.check_outcome(ticker)
        if not outcome.get("ok"):
            return outcome

        ticker = ticker.strip().upper()
        snapshot = self._latest_snapshot(ticker)
        if snapshot is None:
            return {"ok": False, "error": "Snapshot not found"}

        situation = (
            f"[{ticker}] Signal: {outcome.get('signal_was', '?')}. "
            f"Thesis: {outcome.get('thesis', 'N/A')[:200]}. "
            f"Score: {outcome.get('score_at_decision', '?')}/100. "
            f"Price: ${outcome.get('price_at_decision', '?')}."
        )
        outcome_desc = (
            f"After {outcome.get('days_elapsed', '?')} days: "
            f"price {'+' if (outcome.get('price_change_pct') or 0) >= 0 else ''}"
            f"{outcome.get('price_change_pct', '?')}%, "
            f"score change: {outcome.get('score_change', '?')}. "
            f"Quality: {outcome.get('outcome_quality', '?')}."
        )

        if self._memory is not None:
            try:
                self._memory.add(situation, outcome_desc)
                logger.info("reflection: recorded lesson for %s", ticker)
            except Exception as exc:
                logger.warning("reflection: failed to record to memory: %s", exc)

        snapshot["reflected"] = True
        snapshot["reflection_ts"] = datetime.now(timezone.utc).isoformat()
        path = self._root / f"{snapshot['decision_id']}.json"
        path.write_text(json.dumps(snapshot, default=str, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "ticker": ticker,
            "situation": situation,
            "outcome": outcome_desc,
            "outcome_quality": outcome.get("outcome_quality"),
            "recorded_to_memory": self._memory is not None,
        }

    def review_open_decisions(self) -> list[dict[str, Any]]:
        """List decisions older than threshold that haven't been reflected on."""
        now = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []
        for path in sorted(self._root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("reflected"):
                    continue
                dt = datetime.fromisoformat(data.get("ts", ""))
                days = (now - dt).days
                if days >= _REVIEW_THRESHOLD_DAYS:
                    results.append({
                        "decision_id": data.get("decision_id"),
                        "ticker": data.get("ticker"),
                        "signal": data.get("signal"),
                        "thesis": (data.get("thesis") or "")[:100],
                        "days_elapsed": days,
                        "price_at_decision": data.get("price_at_decision"),
                    })
            except Exception:
                continue
        return results

    def _latest_snapshot(self, ticker: str) -> dict[str, Any] | None:
        candidates = sorted(self._root.glob(f"{ticker}_*.json"), reverse=True)
        for path in candidates:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
        return None


def _assess_outcome(signal: str, price_change_pct: float | None) -> str:
    if price_change_pct is None:
        return "unknown"
    bullish = signal in ("BUY", "OVERWEIGHT")
    bearish = signal in ("SELL", "UNDERWEIGHT")
    if bullish:
        if price_change_pct > 5:
            return "good"
        if price_change_pct > -3:
            return "neutral"
        return "bad"
    if bearish:
        if price_change_pct < -5:
            return "good"
        if price_change_pct < 3:
            return "neutral"
        return "bad"
    if abs(price_change_pct) < 10:
        return "good"
    return "neutral"
