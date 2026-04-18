"""MemoryStore — tiered markdown memory for the cockpit agent.

Storage layout under root (~/.tenn/memory/ by default):
    MEMORY.md               — durable: user prefs, key findings
    sessions/
        current.md          — active session turns (JSONL)
        YYYY-MM-DD-HH.md    — archived session logs
    research/
        <TICKER>.md         — per-ticker agent findings
    daily/
        YYYY-MM-DD.md       — compacted daily summaries
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = Path.home() / ".tenn" / "memory"

_DURABLE_FILE = "MEMORY.md"
_SESSION_CURRENT = "sessions/current.md"
_SESSIONS_DIR = "sessions"
_RESEARCH_DIR = "research"
_DAILY_DIR = "daily"


class MemoryStore:
    """Pure filesystem layer: markdown read/write with no external dependencies.

    All paths are relative to *root*. Directories are created on first write.
    Session turns are stored as JSONL lines in ``sessions/current.md``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else _DEFAULT_ROOT

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, relative: str) -> Path:
        return self.root / relative

    def _ensure_parent(self, p: Path) -> None:
        p.parent.mkdir(parents=True, exist_ok=True)

    def _read(self, relative: str) -> str:
        p = self._path(relative)
        if not p.exists():
            return ""
        return p.read_text(encoding="utf-8")

    def _write(self, relative: str, content: str) -> None:
        p = self._path(relative)
        self._ensure_parent(p)
        p.write_text(content, encoding="utf-8")

    def _append(self, relative: str, content: str) -> None:
        p = self._path(relative)
        self._ensure_parent(p)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(content)

    # ------------------------------------------------------------------
    # Session tier: JSONL turns in sessions/current.md
    # ------------------------------------------------------------------

    def append_session_turn(self, role: str, content: str) -> None:
        """Append a single conversation turn to the active session file."""
        turn: dict[str, Any] = {
            "role": role,
            "content": content,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }
        line = json.dumps(turn, ensure_ascii=False)
        self._append(_SESSION_CURRENT, line + "\n")

    def read_session_turns(self) -> list[dict[str, Any]]:
        """Return all turns from the active session as a list of dicts."""
        raw = self._read(_SESSION_CURRENT)
        if not raw.strip():
            return []
        turns: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                turns.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed lines rather than crashing
                continue
        return turns

    def rotate_session(self) -> Path:
        """Archive the current session file and clear it.

        Returns the path of the archived file.
        """
        now = datetime.now(tz=timezone.utc)
        archive_name = f"{_SESSIONS_DIR}/{now.strftime('%Y-%m-%d-%H')}.md"
        archive_path = self._path(archive_name)
        self._ensure_parent(archive_path)

        current = self._path(_SESSION_CURRENT)
        if current.exists():
            content = current.read_text(encoding="utf-8")
            # Append to archive (handles multiple rotations within the same hour)
            with archive_path.open("a", encoding="utf-8") as fh:
                fh.write(content)
            current.write_text("", encoding="utf-8")
        else:
            # Nothing to rotate, but create empty archive so it exists
            archive_path.touch()

        return archive_path

    # ------------------------------------------------------------------
    # Research tier: per-ticker markdown files
    # ------------------------------------------------------------------

    def _research_path(self, ticker: str) -> str:
        return f"{_RESEARCH_DIR}/{ticker.upper()}.md"

    def write_research(self, ticker: str, content: str) -> None:
        """Overwrite research notes for *ticker*."""
        self._write(self._research_path(ticker), content)

    def append_research(self, ticker: str, content: str) -> None:
        """Append *content* to research notes for *ticker* (creates if absent)."""
        existing = self._read(self._research_path(ticker))
        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        self._append(self._research_path(ticker), separator + content)

    def read_research(self, ticker: str) -> str:
        """Return research notes for *ticker*, or empty string if none exist."""
        return self._read(self._research_path(ticker))

    def list_research_tickers(self) -> list[str]:
        """Return ticker names for which research files exist."""
        research_dir = self._path(_RESEARCH_DIR)
        if not research_dir.exists():
            return []
        return [p.stem for p in research_dir.glob("*.md")]

    # ------------------------------------------------------------------
    # Durable tier: MEMORY.md
    # ------------------------------------------------------------------

    def write_durable(self, content: str) -> None:
        """Overwrite the durable memory file."""
        self._write(_DURABLE_FILE, content)

    def append_durable(self, content: str) -> None:
        """Append *content* to the durable memory file."""
        existing = self._read(_DURABLE_FILE)
        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        self._append(_DURABLE_FILE, separator + content)

    def read_durable(self) -> str:
        """Return the full contents of the durable memory file."""
        return self._read(_DURABLE_FILE)

    # ------------------------------------------------------------------
    # Daily tier: compacted daily summaries
    # ------------------------------------------------------------------

    def write_daily(self, summary: str, date: str | None = None) -> None:
        """Write a daily summary for *date* (defaults to today UTC)."""
        if date is None:
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        self._write(f"{_DAILY_DIR}/{date}.md", summary)

    def read_daily(self, date: str | None = None) -> str:
        """Return the daily summary for *date* (defaults to today UTC)."""
        if date is None:
            date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        return self._read(f"{_DAILY_DIR}/{date}.md")
