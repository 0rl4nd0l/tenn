"""
Ticker quarantine: exclude likely non-ASX tickers from universe runs.

Quarantine is applied only when:
- Run used a ticker-universe file (broad sync).
- Run completed successfully (endpoints reachable).
- At least one other ticker in the run had announcements (found > 0).
- This ticker had found=0 and zero existing documents in DB (never had any announcements).

We do NOT quarantine when:
- Run failed (e.g. network/API down).
- Ticker has any existing docs (may simply be up to date).
- User passed explicit --ticker (single-ticker mode).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

QUARANTINE_REASON = "no_announcements_no_existing_docs"
DEFAULT_QUARANTINE_FILENAME = "ticker_quarantine.json"


def _default_path(repo_root: Path) -> Path:
    return repo_root / "config" / DEFAULT_QUARANTINE_FILENAME


def load_quarantine(repo_root: Path, path: Path | None = None) -> Set[str]:
    """Return set of quarantined ticker symbols (uppercase)."""
    p = path or _default_path(repo_root)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        raw = data.get("quarantined") or []
        return {str(t).strip().upper() for t in raw if str(t).strip()}
    except Exception:
        return set()


def save_quarantine(
    repo_root: Path,
    quarantined: List[str] | Set[str],
    path: Path | None = None,
    reason: str = QUARANTINE_REASON,
) -> Path:
    """Write quarantine list to JSON. Deduplicates and sorts."""
    p = path or _default_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tickers = sorted({str(t).strip().upper() for t in quarantined if str(t).strip()})
    data = {
        "quarantined": tickers,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "_comment": "Tickers with found=0 and zero docs in DB when run was healthy; excluded from universe to avoid repeated no-op fetches.",
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def add_to_quarantine(
    repo_root: Path,
    new_tickers: List[str] | Set[str],
    path: Path | None = None,
    reason: str = QUARANTINE_REASON,
) -> List[str]:
    """Merge new_tickers into existing quarantine, save, return list of newly added."""
    existing = load_quarantine(repo_root, path=path)
    to_add = {str(t).strip().upper() for t in new_tickers if str(t).strip()}
    added = list(to_add - existing)
    if not added:
        return []
    merged = existing | to_add
    save_quarantine(repo_root, list(merged), path=path, reason=reason)
    return sorted(added)
