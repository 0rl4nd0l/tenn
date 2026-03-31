"""Strategy workshopping service — user-defined investment criteria and decisions.

Stores global criteria and per-ticker overrides in Cockpit's SQLite state DB.
Builds a formatted context block for LLM injection during analysis.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Categories that criteria can be tagged with.
VALID_CATEGORIES = frozenset(
    {"valuation", "quality", "risk", "momentum", "narrative", "general"}
)

# Maximum criteria per tier when building context block.
_MAX_CRITERIA_PER_TIER = 10

# Staleness threshold in days.
_STALENESS_DAYS = 90


class StrategyService:
    """Manages user-defined investment strategy criteria and decisions."""

    def __init__(self, state_store) -> None:
        self._store = state_store

    # ------------------------------------------------------------------ #
    # Global criteria                                                      #
    # ------------------------------------------------------------------ #

    def add_global(
        self,
        criterion: str,
        category: str = "general",
        priority: int = 5,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a global investment criterion. Returns the inserted row as dict."""
        cat = category.lower() if category.lower() in VALID_CATEGORIES else "general"
        now = datetime.now(timezone.utc).isoformat()
        conn = self._store.conn
        with self._store._lock:
            cur = conn.execute(
                "INSERT INTO global_strategy (criterion, category, priority, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (criterion, cat, priority, notes, now, now),
            )
            conn.commit()
            row_id = cur.lastrowid
        return {"id": row_id, "criterion": criterion, "category": cat, "priority": priority}

    def get_global(self, limit: int = _MAX_CRITERIA_PER_TIER) -> list[dict[str, Any]]:
        """Return global criteria ordered by priority asc, updated_at desc."""
        rows = self._store.conn.execute(
            "SELECT id, criterion, category, priority, notes, created_at, updated_at "
            "FROM global_strategy ORDER BY priority ASC, updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Ticker-specific criteria                                             #
    # ------------------------------------------------------------------ #

    def add_ticker(
        self,
        ticker: str,
        criterion: str,
        category: str = "general",
        priority: int = 5,
        decision: str | None = None,
        decision_rationale: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a ticker-specific criterion or decision."""
        cat = category.lower() if category.lower() in VALID_CATEGORIES else "general"
        upper = ticker.upper()
        now = datetime.now(timezone.utc).isoformat()
        conn = self._store.conn
        with self._store._lock:
            cur = conn.execute(
                "INSERT INTO ticker_strategy "
                "(ticker, criterion, category, priority, decision, decision_rationale, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (upper, criterion, cat, priority, decision, decision_rationale, notes, now, now),
            )
            conn.commit()
            row_id = cur.lastrowid
        return {
            "id": row_id,
            "ticker": upper,
            "criterion": criterion,
            "category": cat,
            "priority": priority,
            "decision": decision,
        }

    def get_ticker(self, ticker: str, limit: int = _MAX_CRITERIA_PER_TIER) -> list[dict[str, Any]]:
        """Return criteria for a specific ticker, ordered by priority asc."""
        rows = self._store.conn.execute(
            "SELECT id, ticker, criterion, category, priority, decision, decision_rationale, "
            "notes, created_at, updated_at "
            "FROM ticker_strategy WHERE ticker = ? ORDER BY priority ASC, updated_at DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_decision(self, ticker: str) -> dict[str, Any] | None:
        """Return the latest decision + rationale for a ticker, or None."""
        row = self._store.conn.execute(
            "SELECT id, ticker, decision, decision_rationale, updated_at "
            "FROM ticker_strategy WHERE ticker = ? AND decision IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1",
            (ticker.upper(),),
        ).fetchone()
        return dict(row) if row else None

    def record_decision(
        self,
        ticker: str,
        decision: str,
        rationale: str,
    ) -> dict[str, Any]:
        """Record a buy/watchlist/avoid decision for a ticker."""
        return self.add_ticker(
            ticker=ticker,
            criterion=f"Decision: {decision}",
            category="general",
            priority=1,
            decision=decision.lower(),
            decision_rationale=rationale,
        )

    # ------------------------------------------------------------------ #
    # Delete                                                                #
    # ------------------------------------------------------------------ #

    def delete(self, row_id: int) -> bool:
        """Delete a criterion by id from either table. Returns True if found."""
        conn = self._store.conn
        with self._store._lock:
            cur = conn.execute("DELETE FROM global_strategy WHERE id = ?", (row_id,))
            if cur.rowcount:
                conn.commit()
                return True
            cur = conn.execute("DELETE FROM ticker_strategy WHERE id = ?", (row_id,))
            conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    # Signal weights                                                       #
    # ------------------------------------------------------------------ #

    # Default composite score weights (must sum to 1.0).
    _DEFAULT_SIGNAL_WEIGHTS: dict[str, float] = {
        "health": 0.40,
        "momentum": 0.25,
        "valuation": 0.20,
        "technical": 0.15,
    }

    def get_signal_weights(self) -> dict[str, float]:
        """Read signal weights from user_preferences. Returns defaults if not set."""
        raw = self._store.get_preference("signal_weights", "")
        if raw:
            try:
                weights = json.loads(raw)
                if isinstance(weights, dict) and all(
                    k in weights for k in self._DEFAULT_SIGNAL_WEIGHTS
                ):
                    return {k: float(weights[k]) for k in self._DEFAULT_SIGNAL_WEIGHTS}
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return dict(self._DEFAULT_SIGNAL_WEIGHTS)

    def set_signal_weights(self, weights: dict[str, float]) -> dict[str, float]:
        """Validate and store signal weights. Weights must sum to ~1.0 (within 0.05 tolerance).

        Returns the stored weights dict.
        Raises ValueError if validation fails.
        """
        required_keys = set(self._DEFAULT_SIGNAL_WEIGHTS)
        provided_keys = set(weights)
        if provided_keys != required_keys:
            missing = required_keys - provided_keys
            extra = provided_keys - required_keys
            parts = []
            if missing:
                parts.append(f"missing: {', '.join(sorted(missing))}")
            if extra:
                parts.append(f"unexpected: {', '.join(sorted(extra))}")
            raise ValueError(f"Invalid weight keys ({'; '.join(parts)}). Required: {', '.join(sorted(required_keys))}")

        clean: dict[str, float] = {}
        for k in required_keys:
            v = weights[k]
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"Weight '{k}' must be a non-negative number, got {v!r}")
            clean[k] = round(float(v), 4)

        total = sum(clean.values())
        if abs(total - 1.0) > 0.05:
            raise ValueError(
                f"Weights must sum to approximately 1.0 (tolerance 0.05). Got {total:.4f}"
            )

        self._store.set_preference("signal_weights", json.dumps(clean))
        return clean

    # ------------------------------------------------------------------ #
    # Context block builder                                                #
    # ------------------------------------------------------------------ #

    def build_context_block(self, ticker: str | None) -> str:
        """Build formatted strategy context for LLM injection.

        Returns empty string if no criteria defined. Caps at ~500 tokens
        by limiting to _MAX_CRITERIA_PER_TIER per tier.
        """
        global_criteria = self.get_global(limit=_MAX_CRITERIA_PER_TIER)
        ticker_criteria = self.get_ticker(ticker) if ticker else []

        if not global_criteria and not ticker_criteria:
            return ""

        lines = [
            "## Investment Strategy",
            "Evaluate this company against the following user-defined criteria.",
            "Do not assert the company meets any criterion — assess whether it does based on evidence.",
            "",
        ]

        if global_criteria:
            lines.append("### Global criteria")
            for c in global_criteria:
                stale = self._staleness_tag(c.get("updated_at", ""))
                prio = f"[P{c['priority']}]" if c["priority"] != 5 else ""
                parts = [f"- {c['criterion']}"]
                if c.get("category") and c["category"] != "general":
                    parts.append(f"({c['category']})")
                if prio:
                    parts.append(prio)
                if stale:
                    parts.append(stale)
                lines.append(" ".join(parts))
            lines.append("")

        if ticker_criteria:
            tkr = ticker.upper() if ticker else "?"
            lines.append(f"### {tkr}-specific criteria")
            for c in ticker_criteria:
                stale = self._staleness_tag(c.get("updated_at", ""))
                prio = f"[P{c['priority']}]" if c["priority"] != 5 else ""
                parts = [f"- {c['criterion']}"]
                if c.get("category") and c["category"] != "general":
                    parts.append(f"({c['category']})")
                if prio:
                    parts.append(prio)
                if c.get("decision"):
                    parts.append(f"[decision: {c['decision']}]")
                if stale:
                    parts.append(stale)
                lines.append(" ".join(parts))

            # Show latest decision summary if one exists
            decision = self.get_decision(tkr)
            if decision and decision.get("decision_rationale"):
                lines.append(
                    f"\nCurrent decision on {tkr}: **{decision['decision']}** — {decision['decision_rationale']}"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _staleness_tag(updated_at: str) -> str:
        """Return a warning tag if the criterion is older than _STALENESS_DAYS."""
        if not updated_at:
            return ""
        try:
            updated = datetime.fromisoformat(updated_at)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - updated).days
            if age_days > _STALENESS_DAYS:
                return f"[stale: {age_days}d old]"
        except (ValueError, TypeError):
            pass
        return ""
