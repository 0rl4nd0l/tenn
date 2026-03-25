"""MemoryCompactor — session context-window management.

Monitors the active session and compacts it when it exceeds configured limits.

Limits (defaults):
    MAX_TURNS  = 40   — number of conversation turns
    MAX_CHARS  = 24_000 — total character count across all turns

Compaction strategy:
    1. Summarise the oldest half of turns via *summarize_fn* (if provided).
    2. Write the summary to the daily file (daily/<YYYY-MM-DD>.md).
    3. Rotate the current session to an archive file.
    4. Re-write only the kept (newer) half of turns to the fresh session.

If *summarize_fn* is None, the oldest half is dropped with a placeholder
message so context window pressure is still relieved.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from cockpit.core.agent.memory.store import MemoryStore

_MAX_TURNS = 40
_MAX_CHARS = 24_000

_DROPPED_MSG = "[older turns dropped during compaction]"


class MemoryCompactor:
    """Monitors and compacts the active session when limits are exceeded.

    Parameters
    ----------
    store:
        A ``MemoryStore`` instance pointing at the memory root.
    summarize_fn:
        Optional callable that takes a list of turn dicts and returns a
        summary string. When absent, older turns are dropped silently.
    max_turns:
        Trigger compaction when the session exceeds this many turns.
    max_chars:
        Trigger compaction when the total session character count exceeds
        this value.
    """

    def __init__(
        self,
        store: MemoryStore,
        summarize_fn: Callable[[list[dict[str, Any]]], str] | None = None,
        max_turns: int = _MAX_TURNS,
        max_chars: int = _MAX_CHARS,
    ) -> None:
        self.store = store
        self.summarize_fn = summarize_fn
        self.max_turns = max_turns
        self.max_chars = max_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def maybe_compact(self) -> bool:
        """Check session limits and compact if exceeded.

        Returns True if compaction was performed, False otherwise.
        """
        turns = self.store.read_session_turns()
        if self._needs_compaction(turns):
            self._compact(turns)
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _needs_compaction(self, turns: list[dict[str, Any]]) -> bool:
        if len(turns) >= self.max_turns:
            return True
        total_chars = sum(len(t.get("content", "")) for t in turns)
        return total_chars >= self.max_chars

    def _compact(self, turns: list[dict[str, Any]]) -> None:
        """Summarise and drop the oldest half, keep the newer half."""
        midpoint = len(turns) // 2
        old_turns = turns[:midpoint]
        kept_turns = turns[midpoint:]

        # Summarise or drop old turns
        if old_turns:
            summary = self._summarise(old_turns)
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            existing_daily = self.store.read_daily(date)
            separator = "\n\n" if existing_daily.strip() else ""
            self.store.write_daily(existing_daily + separator + summary, date=date)

        # Archive and clear the current session
        self.store.rotate_session()

        # Re-write only the kept turns
        for turn in kept_turns:
            self.store.append_session_turn(
                role=turn.get("role", "unknown"),
                content=turn.get("content", ""),
            )

    def _summarise(self, turns: list[dict[str, Any]]) -> str:
        if self.summarize_fn is not None:
            try:
                return self.summarize_fn(turns)
            except Exception:  # noqa: BLE001
                pass
        # No summarize_fn or it failed — emit a placeholder
        return _DROPPED_MSG
