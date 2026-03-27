"""Company dossier service — persistent per-ticker research memory.

Stores research findings as JSONL files at ~/.tenn/memory/dossiers/<TICKER>.jsonl.
Each finding is a single JSON line with ticker, finding text, source, confidence,
category, and timestamp.

This is agent scratch memory — not a source of truth for financial data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = Path.home() / ".tenn" / "memory" / "dossiers"


class CompanyDossierService:
    """JSONL-backed per-ticker research memory."""

    def __init__(self, *, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else _DEFAULT_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(
        self,
        ticker: str,
        finding: str,
        source: str,
        *,
        confidence: float = 0.5,
        category: str = "general",
        source_url: str = "",
    ) -> dict[str, Any]:
        """Append a research finding to a ticker's dossier.

        Returns:
            {"ok": True, "ticker": ..., "entries": <total count>}
        """
        ticker = ticker.strip().upper()
        if not ticker or not finding.strip():
            return {"ok": False, "error": "ticker and finding are required"}

        record = {
            "ticker": ticker,
            "finding": finding.strip(),
            "source": source.strip(),
            "source_url": source_url.strip(),
            "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
            "category": category.strip().lower(),
            "ts": datetime.now(timezone.utc).isoformat(),
        }

        path = self._ticker_path(ticker)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        count = sum(1 for _ in path.open("r", encoding="utf-8"))
        logger.info("dossier: saved finding for %s (%d total)", ticker, count)
        return {"ok": True, "ticker": ticker, "entries": count}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recall(
        self,
        ticker: str,
        *,
        query: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Recall recent findings for a ticker, optionally filtered by keyword.

        Returns:
            {"ok": bool, "ticker": ..., "findings": [...], "total": int}
        """
        ticker = ticker.strip().upper()
        path = self._ticker_path(ticker)
        if not path.exists():
            return {"ok": True, "ticker": ticker, "findings": [], "total": 0}

        findings: list[dict[str, Any]] = []
        for line in path.open("r", encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                findings.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        total = len(findings)

        # Optional keyword filter.
        if query:
            q_lower = query.lower()
            findings = [
                f for f in findings
                if q_lower in f.get("finding", "").lower()
                or q_lower in f.get("category", "").lower()
                or q_lower in f.get("source", "").lower()
            ]

        # Most recent first, limited.
        findings = list(reversed(findings))[:limit]

        return {"ok": True, "ticker": ticker, "findings": findings, "total": total}

    def list_tickers(self) -> list[str]:
        """Return all tickers that have dossier data."""
        return sorted(
            p.stem.upper()
            for p in self._root.glob("*.jsonl")
            if p.stat().st_size > 0
        )

    def summary(self, ticker: str, *, limit: int = 10) -> str:
        """Return a plain-text summary of recent dossier findings."""
        result = self.recall(ticker, limit=limit)
        findings = result.get("findings", [])
        if not findings:
            return f"No dossier entries for {ticker.upper()}."

        lines = [f"Dossier for {ticker.upper()} ({result['total']} total entries):"]
        for f in findings:
            conf = f.get("confidence", 0)
            cat = f.get("category", "")
            ts = f.get("ts", "")[:10]
            lines.append(f"  [{ts}] ({cat}, conf={conf}) {f['finding'][:200]}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ticker_path(self, ticker: str) -> Path:
        return self._root / f"{ticker.upper()}.jsonl"
