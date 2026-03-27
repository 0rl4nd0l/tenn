"""BM25-based situation memory for pattern matching.

Stores (situation_description, outcome) pairs and retrieves similar past
situations using BM25 keyword scoring. Inspired by TradingAgents'
FinancialSituationMemory (Apache 2.0).

Lightweight, offline, no external API dependencies. Uses rank_bm25 (pure Python).
Falls back to simple keyword matching if rank_bm25 is not installed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".tenn" / "memory" / "situations.jsonl"

try:
    from rank_bm25 import BM25Okapi

    _HAS_BM25 = True
except ImportError:
    _HAS_BM25 = False
    logger.info("rank_bm25 not installed — SituationMemory will use simple keyword matching")


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
    return text.lower().split()


class SituationMemory:
    """Stores (situation, outcome) pairs for BM25-based recall."""

    def __init__(self, *, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict[str, str]] = []
        self._index: BM25Okapi | None = None  # type: ignore[assignment]
        self._load()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, situation: str, outcome: str) -> None:
        """Record a situation and its outcome."""
        if not situation.strip() or not outcome.strip():
            return
        entry = {"situation": situation.strip(), "outcome": outcome.strip()}
        self._entries.append(entry)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._rebuild_index()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recall(self, current_situation: str, *, n: int = 3) -> list[dict[str, Any]]:
        """Find similar past situations.

        Returns:
            [{"situation": ..., "outcome": ..., "score": float}, ...]
        """
        if not self._entries or not current_situation.strip():
            return []

        if _HAS_BM25 and self._index is not None:
            return self._bm25_recall(current_situation, n=n)
        return self._keyword_recall(current_situation, n=n)

    # ------------------------------------------------------------------
    # BM25 recall
    # ------------------------------------------------------------------

    def _bm25_recall(self, query: str, *, n: int = 3) -> list[dict[str, Any]]:
        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)  # type: ignore[union-attr]
        scored = sorted(
            zip(range(len(self._entries)), scores),
            key=lambda pair: pair[1],
            reverse=True,
        )
        results: list[dict[str, Any]] = []
        for idx, score in scored[:n]:
            if score <= 0:
                break
            entry = self._entries[idx]
            results.append({
                "situation": entry["situation"],
                "outcome": entry["outcome"],
                "score": round(float(score), 3),
            })
        return results

    # ------------------------------------------------------------------
    # Simple keyword fallback
    # ------------------------------------------------------------------

    def _keyword_recall(self, query: str, *, n: int = 3) -> list[dict[str, Any]]:
        query_tokens = set(_tokenize(query))
        scored: list[tuple[int, float]] = []
        for i, entry in enumerate(self._entries):
            entry_tokens = set(_tokenize(entry["situation"]))
            overlap = len(query_tokens & entry_tokens)
            if overlap > 0:
                score = overlap / max(len(query_tokens), 1)
                scored.append((i, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        results: list[dict[str, Any]] = []
        for idx, score in scored[:n]:
            entry = self._entries[idx]
            results.append({
                "situation": entry["situation"],
                "outcome": entry["outcome"],
                "score": round(score, 3),
            })
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                self._entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if self._entries:
            self._rebuild_index()
            logger.info("SituationMemory: loaded %d entries", len(self._entries))

    def _rebuild_index(self) -> None:
        if not _HAS_BM25 or not self._entries:
            self._index = None
            return
        corpus = [_tokenize(e["situation"]) for e in self._entries]
        self._index = BM25Okapi(corpus)
