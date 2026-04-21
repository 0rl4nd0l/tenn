# Cockpit-UI YouTube Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users drop YouTube URLs in the cockpit-ui chat, see an ingest summary with takeaways and ticker-aware watchlist suggestions, and discuss the transcript contents with the LLM using citation-linked quotes.

**Architecture:** Web-UI orchestrated hybrid retrieval. Backend exposes stateless `/api/commentary/ingest-url`, `/api/commentary/transcripts/*`, `/api/commentary/takeaways`, `/api/commentary/ephemeral-index/*`, `/api/commentary/recent`, and `/api/watchlist/*` endpoints. Cockpit-ui owns per-session attached-source state in React. Short transcripts concat inline; long transcripts route through an ephemeral session-scoped Qdrant collection plus a dedicated `~/.tenn/memory/ephemeral_sessions.sqlite` activity store with a 7-day inactivity cron. Watchlist is a minimal v1 registry seeded by ticker detection in transcripts.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, pydantic v2, qdrant-client, youtube-transcript-api, yt-dlp, sentence-transformers (existing), Next.js 15, React 18, Playwright 1.59, Vitest (to be installed), Zod (existing).

**Source spec:** `docs/superpowers/specs/2026-04-18-cockpit-ui-youtube-ingest-design.md`

---

## Phase 1 — Backend foundation

Sixteen TDD tasks. Each task ends in a green test and a `milestone(youtube-ingest): ...` commit. Run all backend tests from `financial-engine_v2/backend/` unless noted.

### Task 1: Watchlist SQLAlchemy model

**Files:**
- Create: `financial-engine_v2/backend/app/models/watchlist.py`
- Modify: `financial-engine_v2/backend/app/models/__init__.py`
- Test: `financial-engine_v2/backend/tests/test_watchlist_model.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_watchlist_model.py
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.watchlist import Watchlist


def test_watchlist_row_round_trips():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        row = Watchlist(
            ticker="CBA.AX",
            added_at=datetime.now(timezone.utc),
            source_id="yt_abc123",
            note="From transcript: capital management commentary.",
            stance="watch",
        )
        s.add(row)
        s.commit()
        loaded = s.query(Watchlist).filter_by(ticker="CBA.AX").one()
        assert loaded.ticker == "CBA.AX"
        assert loaded.stance == "watch"
        assert loaded.source_id == "yt_abc123"


def test_watchlist_ticker_is_unique():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        s.add(Watchlist(ticker="BHP.AX", added_at=now))
        s.commit()
    with Session(engine) as s:
        s.add(Watchlist(ticker="BHP.AX", added_at=now))
        try:
            s.commit()
        except Exception:
            s.rollback()
        else:
            raise AssertionError("Duplicate ticker insert should have raised")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_model.py -v`
Expected: FAIL with `ModuleNotFoundError: app.models.watchlist`.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/models/watchlist.py
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    stance: Mapped[str | None] = mapped_column(String(32), nullable=True)
```

Add the import line to `app/models/__init__.py`:

```python
from app.models.watchlist import Watchlist  # noqa: F401
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_model.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/models/watchlist.py \
        financial-engine_v2/backend/app/models/__init__.py \
        financial-engine_v2/backend/tests/test_watchlist_model.py
git commit -m "milestone(youtube-ingest): add watchlist SQLAlchemy model

Working: Watchlist model persists ticker as PK with added_at/source_id/note/stance.
Tested: tests/test_watchlist_model.py — 2 passed (round-trip + unique ticker)."
```

---

### Task 2: Alembic migration 0009 for watchlist table

**Files:**
- Create: `financial-engine_v2/backend/app/alembic/versions/0009_add_watchlist.py`
- Test: `financial-engine_v2/backend/tests/test_watchlist_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_watchlist_migration.py
from pathlib import Path

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_migration_0009_creates_watchlist_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    cfg = Config("financial-engine_v2/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0009")

    engine = create_engine(url)
    insp = inspect(engine)
    assert "watchlist" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("watchlist")}
    assert {"ticker", "added_at", "source_id", "note", "stance"} <= cols
    pk = insp.get_pk_constraint("watchlist")
    assert pk["constrained_columns"] == ["ticker"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_migration.py -v`
Expected: FAIL with alembic "Can't locate revision 0009".

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/alembic/versions/0009_add_watchlist.py
"""add watchlist table

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("ticker", sa.String(length=32), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("stance", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("watchlist")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_migration.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/alembic/versions/0009_add_watchlist.py \
        financial-engine_v2/backend/tests/test_watchlist_migration.py
git commit -m "milestone(youtube-ingest): alembic 0009 creates watchlist table

Working: Upgrade creates watchlist(ticker PK, added_at, source_id, note, stance).
Tested: tests/test_watchlist_migration.py — 1 passed (table + columns + PK)."
```

---

### Task 3: SQLite idempotent guard for watchlist

**Files:**
- Create: `financial-engine_v2/backend/scripts/ensure_sqlite_watchlist_table.py`
- Test: `financial-engine_v2/backend/tests/test_ensure_sqlite_watchlist_table.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_ensure_sqlite_watchlist_table.py
import sqlite3
from pathlib import Path

from scripts.ensure_sqlite_watchlist_table import ensure_watchlist_table


def test_creates_table_when_missing(tmp_path: Path) -> None:
    db = tmp_path / "x.sqlite"
    db.touch()
    ensure_watchlist_table(str(db))
    with sqlite3.connect(db) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(watchlist)")]
    assert {"ticker", "added_at", "source_id", "note", "stance"} <= set(cols)


def test_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "x.sqlite"
    db.touch()
    ensure_watchlist_table(str(db))
    ensure_watchlist_table(str(db))
    with sqlite3.connect(db) as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='watchlist'"
        ).fetchone()
    assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_ensure_sqlite_watchlist_table.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/scripts/ensure_sqlite_watchlist_table.py
"""Idempotent guard that creates the watchlist table on a local SQLite DB.

Mirrors the pattern used by ensure_sqlite_asx_created_at_columns.py so the
backend can boot against a pre-existing SQLite file without running Alembic.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS watchlist (
    ticker     TEXT PRIMARY KEY,
    added_at   TEXT NOT NULL,
    source_id  TEXT,
    note       TEXT,
    stance     TEXT
)
"""


def ensure_watchlist_table(db_path: str) -> None:
    path = Path(db_path)
    if not path.exists():
        return
    with sqlite3.connect(path) as conn:
        conn.execute(CREATE_SQL)
        conn.commit()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: ensure_sqlite_watchlist_table.py <db_path>", file=sys.stderr)
        sys.exit(2)
    ensure_watchlist_table(sys.argv[1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_ensure_sqlite_watchlist_table.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/scripts/ensure_sqlite_watchlist_table.py \
        financial-engine_v2/backend/tests/test_ensure_sqlite_watchlist_table.py
git commit -m "milestone(youtube-ingest): idempotent SQLite guard for watchlist

Working: ensure_watchlist_table() creates the table if absent, no-ops if present.
Tested: tests/test_ensure_sqlite_watchlist_table.py — 2 passed (create + idempotent)."
```

---

### Task 4: Watchlist service (add/list/remove)

**Files:**
- Create: `financial-engine_v2/backend/app/services/watchlist_service.py`
- Test: `financial-engine_v2/backend/tests/test_watchlist_service.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_watchlist_service.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.services.watchlist_service import (
    DuplicateTickerError,
    add_to_watchlist,
    list_watchlist,
    remove_from_watchlist,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_add_then_list(session: Session) -> None:
    add_to_watchlist(session, ticker="CBA.AX", source_id="yt_a", note="ok", stance="watch")
    rows = list_watchlist(session)
    assert len(rows) == 1
    assert rows[0].ticker == "CBA.AX"


def test_add_duplicate_raises(session: Session) -> None:
    add_to_watchlist(session, ticker="BHP.AX")
    with pytest.raises(DuplicateTickerError):
        add_to_watchlist(session, ticker="BHP.AX")


def test_remove(session: Session) -> None:
    add_to_watchlist(session, ticker="WBC.AX")
    remove_from_watchlist(session, ticker="WBC.AX")
    assert list_watchlist(session) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_service.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/watchlist_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist


class DuplicateTickerError(Exception):
    """Raised when adding a ticker that already exists in the watchlist."""


def add_to_watchlist(
    session: Session,
    *,
    ticker: str,
    source_id: str | None = None,
    note: str | None = None,
    stance: str | None = None,
) -> Watchlist:
    row = Watchlist(
        ticker=ticker,
        added_at=datetime.now(timezone.utc),
        source_id=source_id,
        note=note,
        stance=stance,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateTickerError(ticker) from exc
    session.refresh(row)
    return row


def list_watchlist(session: Session) -> Sequence[Watchlist]:
    return list(session.scalars(select(Watchlist).order_by(Watchlist.added_at.desc())))


def remove_from_watchlist(session: Session, *, ticker: str) -> bool:
    row = session.get(Watchlist, ticker)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/watchlist_service.py \
        financial-engine_v2/backend/tests/test_watchlist_service.py
git commit -m "milestone(youtube-ingest): watchlist service add/list/remove

Working: add_to_watchlist raises DuplicateTickerError on conflict; list/remove work.
Tested: tests/test_watchlist_service.py — 3 passed."
```

---

### Task 5: Watchlist FastAPI router

**Files:**
- Create: `financial-engine_v2/backend/app/api/watchlist.py`
- Modify: `financial-engine_v2/backend/app/main.py`
- Test: `financial-engine_v2/backend/tests/test_watchlist_api.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_watchlist_api.py
import os
from fastapi.testclient import TestClient

from app.main import app


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_add_list_remove_cycle():
    with TestClient(app) as client:
        r = client.post(
            "/api/watchlist",
            headers=_headers(),
            json={"ticker": "CBA.AX", "source_id": "yt_a", "note": "test", "stance": "watch"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["ticker"] == "CBA.AX"

        r = client.get("/api/watchlist", headers=_headers())
        assert r.status_code == 200
        assert any(x["ticker"] == "CBA.AX" for x in r.json()["items"])

        r = client.delete("/api/watchlist/CBA.AX", headers=_headers())
        assert r.status_code == 204


def test_duplicate_returns_409():
    with TestClient(app) as client:
        client.post("/api/watchlist", headers=_headers(), json={"ticker": "BHP.AX"})
        r = client.post("/api/watchlist", headers=_headers(), json={"ticker": "BHP.AX"})
        assert r.status_code == 409
        # cleanup
        client.delete("/api/watchlist/BHP.AX", headers=_headers())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_api.py -v`
Expected: FAIL — 404 from missing endpoints.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/api/watchlist.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes import require_api_key
from app.core.db import get_db
from app.services.watchlist_service import (
    DuplicateTickerError,
    add_to_watchlist,
    list_watchlist,
    remove_from_watchlist,
)

router = APIRouter()


class AddRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    source_id: str | None = None
    note: str | None = None
    stance: str | None = None


class WatchlistItem(BaseModel):
    ticker: str
    added_at: str
    source_id: str | None
    note: str | None
    stance: str | None


class ListResponse(BaseModel):
    items: list[WatchlistItem]


@router.post("", status_code=201, response_model=WatchlistItem, dependencies=[Depends(require_api_key)])
def add(req: AddRequest, db: Session = Depends(get_db)) -> WatchlistItem:
    try:
        row = add_to_watchlist(
            db,
            ticker=req.ticker,
            source_id=req.source_id,
            note=req.note,
            stance=req.stance,
        )
    except DuplicateTickerError as exc:
        raise HTTPException(status_code=409, detail=f"ticker already in watchlist: {exc}")
    return WatchlistItem(
        ticker=row.ticker,
        added_at=row.added_at.isoformat(),
        source_id=row.source_id,
        note=row.note,
        stance=row.stance,
    )


@router.get("", response_model=ListResponse, dependencies=[Depends(require_api_key)])
def listing(db: Session = Depends(get_db)) -> ListResponse:
    rows = list_watchlist(db)
    return ListResponse(
        items=[
            WatchlistItem(
                ticker=r.ticker,
                added_at=r.added_at.isoformat(),
                source_id=r.source_id,
                note=r.note,
                stance=r.stance,
            )
            for r in rows
        ]
    )


@router.delete("/{ticker}", status_code=204, dependencies=[Depends(require_api_key)])
def remove(ticker: str, db: Session = Depends(get_db)) -> Response:
    removed = remove_from_watchlist(db, ticker=ticker)
    if not removed:
        raise HTTPException(status_code=404, detail="ticker not found")
    return Response(status_code=204)
```

Add to `app/main.py` near the other router registrations:

```python
from app.api.watchlist import router as watchlist_router
app.include_router(watchlist_router, prefix="/api/watchlist", tags=["watchlist"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_watchlist_api.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/watchlist.py \
        financial-engine_v2/backend/app/main.py \
        financial-engine_v2/backend/tests/test_watchlist_api.py
git commit -m "milestone(youtube-ingest): watchlist REST endpoints

Working: POST/GET/DELETE /api/watchlist; 409 on duplicate ticker.
Tested: tests/test_watchlist_api.py — 2 passed (cycle + duplicate-409)."
```

---

### Task 6: Ticker detector utility

**Files:**
- Create: `financial-engine_v2/backend/app/services/ticker_detector.py`
- Test: `financial-engine_v2/backend/tests/test_ticker_detector.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_ticker_detector.py
from app.services.ticker_detector import detect_tickers


def test_detects_asx_codes_with_suffix():
    text = "Looking at CBA.AX and bhp.ax today, also WBC."
    found = detect_tickers(text)
    assert {"CBA.AX", "BHP.AX", "WBC.AX"} <= set(found)


def test_ignores_common_acronyms():
    text = "The CEO said GDP, CPI, and RBA matter."
    assert detect_tickers(text) == []


def test_company_name_maps_to_ticker():
    text = "Commonwealth Bank of Australia reported strong growth"
    found = detect_tickers(text)
    assert "CBA.AX" in found


def test_dedupes_and_sorts():
    text = "CBA CBA.AX cba.ax"
    assert detect_tickers(text) == ["CBA.AX"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_ticker_detector.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/ticker_detector.py
"""Heuristic ASX ticker detection used for YouTube transcript takeaways.

Not authoritative — purely a surfacing hint for the watchlist suggestion UI.
Users always confirm adds; the only "guarantee" is that blatant common
acronyms (GDP, CPI, RBA, CEO, CFO, ...) never appear as tickers.
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "CEO", "CFO", "COO", "CTO", "GDP", "CPI", "RBA", "ASX", "ETF", "IPO",
    "USD", "AUD", "EUR", "GBP", "EPS", "PE", "YOY", "QOQ", "AI", "ML",
}

# Minimal name → ticker map. Extend as needed; deliberately small to keep
# false positives low. Lowercase keys, canonical ticker values.
_NAME_TO_TICKER: dict[str, str] = {
    "commonwealth bank of australia": "CBA.AX",
    "commonwealth bank": "CBA.AX",
    "bhp group": "BHP.AX",
    "bhp": "BHP.AX",
    "westpac": "WBC.AX",
    "national australia bank": "NAB.AX",
    "anz": "ANZ.AX",
    "rio tinto": "RIO.AX",
    "fortescue": "FMG.AX",
    "woolworths": "WOW.AX",
    "coles": "COL.AX",
    "wesfarmers": "WES.AX",
    "telstra": "TLS.AX",
    "csl": "CSL.AX",
    "macquarie": "MQG.AX",
    "qantas": "QAN.AX",
}

_EXPLICIT_TICKER_RE = re.compile(r"\b([A-Z]{2,5})\.AX\b", re.IGNORECASE)
_BARE_TICKER_RE = re.compile(r"\b([A-Z]{3,4})\b")


def detect_tickers(text: str) -> list[str]:
    """Return a sorted, deduped list of ASX tickers found in `text`."""
    if not text:
        return []
    found: set[str] = set()

    for m in _EXPLICIT_TICKER_RE.finditer(text):
        found.add(f"{m.group(1).upper()}.AX")

    lowered = text.lower()
    for name, ticker in _NAME_TO_TICKER.items():
        if name in lowered:
            found.add(ticker)

    for m in _BARE_TICKER_RE.finditer(text):
        code = m.group(1).upper()
        if code in _STOPWORDS:
            continue
        if code in {t.split(".")[0] for t in _NAME_TO_TICKER.values()}:
            found.add(f"{code}.AX")

    return sorted(found)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_ticker_detector.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/ticker_detector.py \
        financial-engine_v2/backend/tests/test_ticker_detector.py
git commit -m "milestone(youtube-ingest): heuristic ticker detector

Working: detect_tickers finds CBA.AX-style codes, maps common company names, dedupes.
Tested: tests/test_ticker_detector.py — 4 passed."
```

---

### Task 7: YouTube transcript fetcher

**Files:**
- Create: `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py`
- Test: `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py
from unittest.mock import patch

import pytest

from app.services.youtube_transcript_fetcher import (
    TranscriptFetchError,
    extract_video_id,
    fetch_transcript,
)


def test_extract_video_id_variants():
    assert extract_video_id("https://youtu.be/abc123") == "abc123"
    assert extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert extract_video_id("https://www.youtube.com/watch?v=abc123&t=60") == "abc123"
    assert extract_video_id("https://youtube.com/shorts/abc123") == "abc123"


def test_extract_video_id_invalid():
    with pytest.raises(TranscriptFetchError):
        extract_video_id("https://example.com/video")


def test_fetch_transcript_returns_segments():
    fake_segments = [
        {"text": "hello", "start": 0.0, "duration": 1.0},
        {"text": "world", "start": 1.0, "duration": 1.0},
    ]
    with patch(
        "app.services.youtube_transcript_fetcher.YouTubeTranscriptApi"
    ) as mock_api:
        mock_api.get_transcript.return_value = fake_segments
        result = fetch_transcript("https://youtu.be/abc123")
    assert result.video_id == "abc123"
    assert result.segments == fake_segments
    assert result.title is not None  # falls back to video_id if unresolved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_youtube_transcript_fetcher.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:  # pragma: no cover
    YouTubeTranscriptApi = None  # type: ignore[assignment]


class TranscriptFetchError(Exception):
    """Raised when a YouTube URL cannot be resolved to a transcript."""


@dataclass(frozen=True)
class FetchedTranscript:
    video_id: str
    title: str
    segments: list[dict[str, Any]]

    @property
    def full_text(self) -> str:
        return " ".join(seg["text"].strip() for seg in self.segments if seg.get("text"))


_YOUTU_BE_RE = re.compile(r"youtu\.be/([A-Za-z0-9_-]{6,})")
_SHORTS_RE = re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]{6,})")


def extract_video_id(url: str) -> str:
    if not url:
        raise TranscriptFetchError("empty url")
    m = _YOUTU_BE_RE.search(url)
    if m:
        return m.group(1)
    m = _SHORTS_RE.search(url)
    if m:
        return m.group(1)
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        v = parse_qs(parsed.query).get("v", [])
        if v:
            return v[0]
    raise TranscriptFetchError(f"not a recognisable YouTube URL: {url!r}")


def fetch_transcript(url: str) -> FetchedTranscript:
    if YouTubeTranscriptApi is None:
        raise TranscriptFetchError("youtube_transcript_api not installed")
    video_id = extract_video_id(url)
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as exc:  # noqa: BLE001 — library raises many unrelated types
        raise TranscriptFetchError(f"transcript fetch failed for {video_id}") from exc
    title = _resolve_title(video_id) or video_id
    return FetchedTranscript(video_id=video_id, title=title, segments=list(segments))


def _resolve_title(video_id: str) -> str | None:
    """Best-effort title resolution; returns None on any failure.

    We call yt-dlp only when it's importable. This keeps unit tests hermetic
    (the patched test never hits this path).
    """
    try:
        from yt_dlp import YoutubeDL  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(f"https://youtu.be/{video_id}", download=False)
        return info.get("title") if isinstance(info, dict) else None
    except Exception:  # noqa: BLE001
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_youtube_transcript_fetcher.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py \
        financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py
git commit -m "milestone(youtube-ingest): transcript fetcher with URL parser

Working: extract_video_id handles youtu.be/watch?v=/shorts; fetch_transcript wraps youtube_transcript_api with TranscriptFetchError.
Tested: tests/test_youtube_transcript_fetcher.py — 3 passed."
```

---

### Task 8: Extend commentary_ingest to accept structured segments

**Files:**
- Modify: `financial-engine_v2/backend/app/services/commentary_ingest.py`
- Test: `financial-engine_v2/backend/tests/test_commentary_ingest_segments.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_commentary_ingest_segments.py
from pathlib import Path
from unittest.mock import MagicMock

from app.services.commentary_ingest import ingest_transcript


def test_ingest_records_segment_start_per_chunk(tmp_path: Path) -> None:
    qdrant = MagicMock()
    segments = [
        {"text": "First thing mentioned.", "start": 0.0, "duration": 3.0},
        {"text": "Second thing, later on.", "start": 3.0, "duration": 4.0},
        {"text": "Third thing near the end.", "start": 7.0, "duration": 5.0},
    ]
    result = ingest_transcript(
        transcript_text="First thing mentioned. Second thing, later on. Third thing near the end.",
        source_name="Test video",
        source_type="youtube",
        source_id="yt_testvid",
        qdrant_client=qdrant,
        registry_path=tmp_path / "registry.json",
        memos_path=tmp_path / "memos",
        collection_name="commentary_chunks",
        segments=segments,
        staged=True,
        staged_dir=tmp_path / "staged_chunks",
    )
    assert result.source_id == "yt_testvid"
    assert result.chunk_count >= 1
    staged_file = tmp_path / "staged_chunks" / "yt_testvid.jsonl"
    assert staged_file.exists()
    lines = staged_file.read_text().splitlines()
    assert lines, "expected at least one staged chunk"
    import json
    first = json.loads(lines[0])
    assert "segment_start_seconds" in first
    assert first["segment_start_seconds"] >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ingest_segments.py -v`
Expected: FAIL — `segments`/`staged` kwargs not accepted.

- [ ] **Step 3: Write minimal implementation**

Extend `ingest_transcript` to accept `segments: list[dict] | None = None`, `staged: bool = False`, and `staged_dir: Path | None = None`. When staged, write each chunk as a JSONL line to `<staged_dir>/<source_id>.jsonl` with fields: `chunk_id`, `text`, `segment_start_seconds`, `segment_end_seconds`, `source_id`, `source_type`, `source_name`. Map each chunk to its nearest segment start by cumulative character offset. Do NOT write to Qdrant when `staged=True`. Do not remove existing behavior — non-staged ingests must still push to Qdrant and registry as before.

Add a `ChunkMeta` helper at the top of the file:

```python
@dataclass(frozen=True)
class ChunkMeta:
    chunk_id: str
    text: str
    segment_start_seconds: float
    segment_end_seconds: float
```

Core staged path:

```python
def _stage_chunks(
    *,
    chunks: list[ChunkMeta],
    staged_dir: Path,
    source_id: str,
    source_name: str,
    source_type: str,
) -> Path:
    staged_dir.mkdir(parents=True, exist_ok=True)
    target = staged_dir / f"{source_id}.jsonl"
    with target.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "segment_start_seconds": c.segment_start_seconds,
                "segment_end_seconds": c.segment_end_seconds,
                "source_id": source_id,
                "source_name": source_name,
                "source_type": source_type,
            }) + "\n")
    return target
```

Return a result dataclass with `source_id` and `chunk_count`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ingest_segments.py -v`
Expected: 1 passed.

- [ ] **Step 5: Run the existing commentary tests to confirm no regression**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_api.py tests/test_commentary_ingest.py -v`
Expected: all previously-passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/backend/app/services/commentary_ingest.py \
        financial-engine_v2/backend/tests/test_commentary_ingest_segments.py
git commit -m "milestone(youtube-ingest): segment-aware staged ingest

Working: ingest_transcript now accepts segments+staged, writes JSONL with segment_start_seconds per chunk; non-staged path unchanged.
Tested: tests/test_commentary_ingest_segments.py — 1 passed; prior commentary tests still green."
```

---

### Task 9: Ingest-URL endpoint

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Test: `financial-engine_v2/backend/tests/test_commentary_ingest_url_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_commentary_ingest_url_endpoint.py
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.youtube_transcript_fetcher import FetchedTranscript


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_ingest_url_returns_summary_and_detected_tickers():
    transcript = FetchedTranscript(
        video_id="abc123",
        title="CBA results review",
        segments=[
            {"text": "CBA.AX delivered strong results.", "start": 0.0, "duration": 3.0},
            {"text": "BHP also featured in commentary.", "start": 3.0, "duration": 3.0},
        ],
    )
    with patch("app.api.commentary.fetch_transcript", return_value=transcript), \
         patch("app.api.commentary.ingest_transcript") as mock_ingest:
        mock_ingest.return_value = MagicMock(source_id="yt_abc123", chunk_count=2)
        with TestClient(app) as client:
            r = client.post(
                "/api/commentary/ingest-url",
                headers=_headers(),
                json={"url": "https://youtu.be/abc123"},
            )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_id"] == "yt_abc123"
    assert body["title"] == "CBA results review"
    assert body["chunk_count"] == 2
    assert "CBA.AX" in body["detected_tickers"]
    assert body["status"] == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ingest_url_endpoint.py -v`
Expected: FAIL — endpoint does not exist.

- [ ] **Step 3: Write minimal implementation**

Add to `app/api/commentary.py`:

```python
from pydantic import BaseModel, HttpUrl
from app.services.youtube_transcript_fetcher import (
    TranscriptFetchError,
    fetch_transcript,
)
from app.services.commentary_ingest import ingest_transcript
from app.services.ticker_detector import detect_tickers


class IngestUrlRequest(BaseModel):
    url: HttpUrl
    source_name: str | None = None


class IngestUrlResponse(BaseModel):
    source_id: str
    title: str
    chunk_count: int
    detected_tickers: list[str]
    status: str  # "pending"


@router.post("/ingest-url", response_model=IngestUrlResponse, dependencies=[Depends(require_api_key)])
def ingest_url(req: IngestUrlRequest) -> IngestUrlResponse:
    try:
        transcript = fetch_transcript(str(req.url))
    except TranscriptFetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    source_id = f"yt_{transcript.video_id}"
    result = ingest_transcript(
        transcript_text=transcript.full_text,
        source_name=req.source_name or transcript.title,
        source_type="youtube",
        source_id=source_id,
        segments=transcript.segments,
        staged=True,
        staged_dir=STAGED_CHUNKS_DIR,
        qdrant_client=None,
        registry_path=None,
        memos_path=None,
        collection_name="commentary_chunks",
    )
    tickers = detect_tickers(transcript.full_text)
    return IngestUrlResponse(
        source_id=result.source_id,
        title=transcript.title,
        chunk_count=result.chunk_count,
        detected_tickers=tickers,
        status="pending",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ingest_url_endpoint.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_commentary_ingest_url_endpoint.py
git commit -m "milestone(youtube-ingest): POST /api/commentary/ingest-url

Working: URL ingest stages chunks under ~/.tenn/memory/staged_chunks and returns source_id + detected_tickers + status=pending.
Tested: tests/test_commentary_ingest_url_endpoint.py — 1 passed."
```

---

### Task 10: GET /commentary/transcripts/{source_id}

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Test: `financial-engine_v2/backend/tests/test_commentary_transcripts_get.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_commentary_transcripts_get.py
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import commentary as commentary_mod
from app.main import app


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_resolves_staged_transcript(tmp_path: Path, monkeypatch):
    staged = tmp_path / "staged_chunks"
    staged.mkdir()
    (staged / "yt_pending.jsonl").write_text(
        json.dumps({
            "chunk_id": "c1", "text": "hello", "segment_start_seconds": 0.0,
            "segment_end_seconds": 1.0, "source_id": "yt_pending",
            "source_name": "Pending Vid", "source_type": "youtube",
        }) + "\n"
    )
    monkeypatch.setattr(commentary_mod, "STAGED_CHUNKS_DIR", staged)

    with TestClient(app) as client:
        r = client.get("/api/commentary/transcripts/yt_pending", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["source_id"] == "yt_pending"
    assert len(body["chunks"]) == 1


def test_missing_returns_404(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(commentary_mod, "STAGED_CHUNKS_DIR", tmp_path / "empty")
    with TestClient(app) as client:
        r = client.get("/api/commentary/transcripts/yt_nope", headers=_headers())
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_transcripts_get.py -v`
Expected: FAIL — endpoint missing.

- [ ] **Step 3: Write minimal implementation**

Add to `app/api/commentary.py`:

```python
class TranscriptChunk(BaseModel):
    chunk_id: str
    text: str
    segment_start_seconds: float
    segment_end_seconds: float


class TranscriptResponse(BaseModel):
    source_id: str
    source_name: str
    status: str  # "pending" | "approved"
    chunks: list[TranscriptChunk]


@router.get(
    "/transcripts/{source_id}",
    response_model=TranscriptResponse,
    dependencies=[Depends(require_api_key)],
)
def get_transcript(source_id: str) -> TranscriptResponse:
    staged_file = STAGED_CHUNKS_DIR / f"{source_id}.jsonl"
    if staged_file.exists():
        chunks: list[TranscriptChunk] = []
        source_name = source_id
        for line in staged_file.read_text().splitlines():
            obj = json.loads(line)
            chunks.append(TranscriptChunk(
                chunk_id=obj["chunk_id"],
                text=obj["text"],
                segment_start_seconds=float(obj["segment_start_seconds"]),
                segment_end_seconds=float(obj["segment_end_seconds"]),
            ))
            source_name = obj.get("source_name", source_name)
        return TranscriptResponse(
            source_id=source_id, source_name=source_name,
            status="pending", chunks=chunks,
        )

    approved = _load_approved_transcript(source_id)
    if approved is not None:
        return approved

    raise HTTPException(status_code=404, detail=f"transcript not found: {source_id}")


def _load_approved_transcript(source_id: str) -> TranscriptResponse | None:
    # registry lookup — implementation reuses existing registry load path
    registry_path = Path("~/.tenn/memory/commentary_registry.json").expanduser()
    if not registry_path.exists():
        return None
    registry = json.loads(registry_path.read_text())
    entry = registry.get(source_id)
    if not entry:
        return None
    chunks = [
        TranscriptChunk(
            chunk_id=c["chunk_id"],
            text=c["text"],
            segment_start_seconds=float(c.get("segment_start_seconds", 0.0)),
            segment_end_seconds=float(c.get("segment_end_seconds", 0.0)),
        )
        for c in entry.get("chunks", [])
    ]
    return TranscriptResponse(
        source_id=source_id,
        source_name=entry.get("source_name", source_id),
        status="approved",
        chunks=chunks,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_transcripts_get.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_commentary_transcripts_get.py
git commit -m "milestone(youtube-ingest): GET /api/commentary/transcripts/{id}

Working: Resolves staged JSONL (pending) or approved registry, 404 otherwise.
Tested: tests/test_commentary_transcripts_get.py — 2 passed."
```

---

### Task 11: Ephemeral Qdrant service

**Files:**
- Create: `financial-engine_v2/backend/app/services/commentary_ephemeral.py`
- Test: `financial-engine_v2/backend/tests/test_commentary_ephemeral.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_commentary_ephemeral.py
from unittest.mock import MagicMock

from app.services.commentary_ephemeral import (
    build_collection_name,
    ensure_collection,
    index_chunks,
    search_chunks,
)


def test_collection_name_is_session_scoped():
    name = build_collection_name("sess-123")
    assert name == "commentary_ephemeral_sess-123"


def test_ensure_collection_creates_once():
    client = MagicMock()
    client.collection_exists.return_value = False
    ensure_collection(client, "sess-abc", vector_size=384)
    client.create_collection.assert_called_once()


def test_search_passes_session_filter():
    client = MagicMock()
    client.search.return_value = []
    search_chunks(client, "sess-abc", query_vector=[0.0] * 384, limit=5)
    call = client.search.call_args
    assert call.kwargs["collection_name"] == "commentary_ephemeral_sess-abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ephemeral.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/commentary_ephemeral.py
"""Session-scoped Qdrant collections for long YouTube transcripts.

Each chat session that attaches a long transcript gets its own
`commentary_ephemeral_<session_id>` collection. A separate activity store
(see ephemeral_sessions_store.py) drives the 7-day cleanup cron.
"""
from __future__ import annotations

from typing import Any, Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


def build_collection_name(session_id: str) -> str:
    return f"commentary_ephemeral_{session_id}"


def ensure_collection(
    client: QdrantClient, session_id: str, *, vector_size: int
) -> str:
    name = build_collection_name(session_id)
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    return name


def index_chunks(
    client: QdrantClient,
    session_id: str,
    *,
    points: Sequence[PointStruct],
) -> None:
    client.upsert(collection_name=build_collection_name(session_id), points=list(points))


def search_chunks(
    client: QdrantClient,
    session_id: str,
    *,
    query_vector: list[float],
    limit: int = 5,
    query_filter: Any | None = None,
):
    return client.search(
        collection_name=build_collection_name(session_id),
        query_vector=query_vector,
        limit=limit,
        query_filter=query_filter,
    )


def delete_collection(client: QdrantClient, session_id: str) -> None:
    name = build_collection_name(session_id)
    if client.collection_exists(name):
        client.delete_collection(collection_name=name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_ephemeral.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/commentary_ephemeral.py \
        financial-engine_v2/backend/tests/test_commentary_ephemeral.py
git commit -m "milestone(youtube-ingest): commentary_ephemeral service

Working: build_collection_name/ensure_collection/index_chunks/search_chunks/delete_collection scoped per session_id.
Tested: tests/test_commentary_ephemeral.py — 3 passed."
```

---

### Task 12: Ephemeral session activity store

**Files:**
- Create: `financial-engine_v2/backend/app/services/ephemeral_sessions_store.py`
- Test: `financial-engine_v2/backend/tests/test_ephemeral_sessions_store.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_ephemeral_sessions_store.py
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.ephemeral_sessions_store import (
    list_stale_sessions,
    mark_session_active,
    open_store,
    remove_session,
)


def test_upsert_and_stale(tmp_path: Path) -> None:
    db = tmp_path / "ephem.sqlite"
    with open_store(db) as store:
        mark_session_active(store, "s1", collection_name="commentary_ephemeral_s1")
        mark_session_active(store, "s2", collection_name="commentary_ephemeral_s2")
        now = datetime.now(timezone.utc)
        store.execute(
            "UPDATE ephemeral_sessions SET last_activity_at = ? WHERE session_id = ?",
            ((now - timedelta(days=8)).isoformat(), "s1"),
        )
        store.commit()
        stale = list_stale_sessions(store, older_than=timedelta(days=7))
    assert [s.session_id for s in stale] == ["s1"]


def test_remove_session(tmp_path: Path) -> None:
    db = tmp_path / "ephem.sqlite"
    with open_store(db) as store:
        mark_session_active(store, "s1", collection_name="commentary_ephemeral_s1")
        remove_session(store, "s1")
        rows = store.execute("SELECT session_id FROM ephemeral_sessions").fetchall()
    assert rows == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_ephemeral_sessions_store.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/ephemeral_sessions_store.py
"""Dedicated activity ledger for ephemeral session-scoped Qdrant collections.

Schema is intentionally standalone to avoid coupling to chat history.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_PATH = Path("~/.tenn/memory/ephemeral_sessions.sqlite").expanduser()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ephemeral_sessions (
    session_id       TEXT PRIMARY KEY,
    last_activity_at TEXT NOT NULL,
    collection_name  TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class EphemeralSessionRow:
    session_id: str
    last_activity_at: datetime
    collection_name: str


@contextmanager
def open_store(path: Path = DEFAULT_PATH) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
        yield conn
    finally:
        conn.close()


def mark_session_active(
    conn: sqlite3.Connection, session_id: str, *, collection_name: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO ephemeral_sessions(session_id, last_activity_at, collection_name)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            last_activity_at = excluded.last_activity_at,
            collection_name  = excluded.collection_name
        """,
        (session_id, now, collection_name),
    )
    conn.commit()


def list_stale_sessions(
    conn: sqlite3.Connection, *, older_than: timedelta
) -> list[EphemeralSessionRow]:
    cutoff = (datetime.now(timezone.utc) - older_than).isoformat()
    rows = conn.execute(
        "SELECT session_id, last_activity_at, collection_name FROM ephemeral_sessions WHERE last_activity_at < ?",
        (cutoff,),
    ).fetchall()
    return [
        EphemeralSessionRow(
            session_id=r[0],
            last_activity_at=datetime.fromisoformat(r[1]),
            collection_name=r[2],
        )
        for r in rows
    ]


def remove_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM ephemeral_sessions WHERE session_id = ?", (session_id,))
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_ephemeral_sessions_store.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/ephemeral_sessions_store.py \
        financial-engine_v2/backend/tests/test_ephemeral_sessions_store.py
git commit -m "milestone(youtube-ingest): ephemeral session activity store

Working: open_store/mark_session_active/list_stale_sessions/remove_session against ~/.tenn/memory/ephemeral_sessions.sqlite.
Tested: tests/test_ephemeral_sessions_store.py — 2 passed."
```

---

### Task 13: Ephemeral-index HTTP endpoints

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Test: `financial-engine_v2/backend/tests/test_ephemeral_index_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_ephemeral_index_endpoints.py
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_build_index_marks_session_active():
    fake_qdrant = MagicMock()
    fake_qdrant.collection_exists.return_value = False
    with patch("app.api.commentary.get_qdrant_client", return_value=fake_qdrant), \
         patch("app.api.commentary.embed_texts", return_value=[[0.1] * 384] * 2), \
         patch("app.api.commentary.load_staged_chunks", return_value=[
             {"chunk_id": "c1", "text": "a", "segment_start_seconds": 0.0, "segment_end_seconds": 1.0, "source_id": "yt_x", "source_name": "V", "source_type": "youtube"},
             {"chunk_id": "c2", "text": "b", "segment_start_seconds": 1.0, "segment_end_seconds": 2.0, "source_id": "yt_x", "source_name": "V", "source_type": "youtube"},
         ]), \
         patch("app.api.commentary.mark_session_active") as mock_mark:
        with TestClient(app) as client:
            r = client.post(
                "/api/commentary/ephemeral-index",
                headers=_headers(),
                json={"session_id": "sess-1", "source_ids": ["yt_x"]},
            )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["collection_name"] == "commentary_ephemeral_sess-1"
    assert body["indexed_chunks"] == 2
    mock_mark.assert_called_once()


def test_delete_collection_flow():
    fake_qdrant = MagicMock()
    with patch("app.api.commentary.get_qdrant_client", return_value=fake_qdrant), \
         patch("app.api.commentary.remove_session") as mock_remove:
        with TestClient(app) as client:
            r = client.delete(
                "/api/commentary/ephemeral-index/sess-1", headers=_headers()
            )
    assert r.status_code == 204
    fake_qdrant.delete_collection.assert_called_once()
    mock_remove.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_ephemeral_index_endpoints.py -v`
Expected: FAIL — endpoints missing.

- [ ] **Step 3: Write minimal implementation**

In `app/api/commentary.py`:

```python
from app.services.commentary_ephemeral import (
    build_collection_name,
    delete_collection,
    ensure_collection,
    index_chunks,
)
from app.services.ephemeral_sessions_store import (
    mark_session_active,
    open_store,
    remove_session,
)

VECTOR_SIZE = 384  # matches all-MiniLM-L6-v2


class EphemeralIndexRequest(BaseModel):
    session_id: str
    source_ids: list[str]


class EphemeralIndexResponse(BaseModel):
    session_id: str
    collection_name: str
    indexed_chunks: int


def load_staged_chunks(source_ids: list[str]) -> list[dict]:
    chunks: list[dict] = []
    for sid in source_ids:
        p = STAGED_CHUNKS_DIR / f"{sid}.jsonl"
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            chunks.append(json.loads(line))
    return chunks


@router.post(
    "/ephemeral-index",
    response_model=EphemeralIndexResponse,
    dependencies=[Depends(require_api_key)],
)
def build_ephemeral_index(req: EphemeralIndexRequest) -> EphemeralIndexResponse:
    if not req.source_ids:
        raise HTTPException(status_code=400, detail="source_ids must not be empty")
    chunks = load_staged_chunks(req.source_ids)
    if not chunks:
        raise HTTPException(status_code=404, detail="no staged chunks found for given source_ids")

    client = get_qdrant_client()
    ensure_collection(client, req.session_id, vector_size=VECTOR_SIZE)
    vectors = embed_texts([c["text"] for c in chunks])
    points = [
        PointStruct(
            id=c["chunk_id"],
            vector=v,
            payload={
                "text": c["text"],
                "source_id": c["source_id"],
                "source_name": c["source_name"],
                "source_type": c["source_type"],
                "segment_start_seconds": c["segment_start_seconds"],
                "segment_end_seconds": c["segment_end_seconds"],
                "source_kind": "ephemeral",
            },
        )
        for c, v in zip(chunks, vectors)
    ]
    index_chunks(client, req.session_id, points=points)

    collection_name = build_collection_name(req.session_id)
    with open_store() as store:
        mark_session_active(store, req.session_id, collection_name=collection_name)

    return EphemeralIndexResponse(
        session_id=req.session_id,
        collection_name=collection_name,
        indexed_chunks=len(points),
    )


@router.delete(
    "/ephemeral-index/{session_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
def delete_ephemeral_index(session_id: str) -> Response:
    client = get_qdrant_client()
    delete_collection(client, session_id)
    with open_store() as store:
        remove_session(store, session_id)
    return Response(status_code=204)
```

Notes for the implementer: `get_qdrant_client`, `embed_texts`, and `PointStruct` are already imported by the existing commentary module; reuse whatever helpers exist rather than creating new ones. The test patches them by name at `app.api.commentary.*`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_ephemeral_index_endpoints.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_ephemeral_index_endpoints.py
git commit -m "milestone(youtube-ingest): ephemeral-index POST/DELETE endpoints

Working: POST builds per-session Qdrant collection + marks activity; DELETE drops both.
Tested: tests/test_ephemeral_index_endpoints.py — 2 passed."
```

---

### Task 14: Cleanup cron script (7-day inactivity)

**Files:**
- Create: `financial-engine_v2/backend/scripts/cleanup_ephemeral_sessions.py`
- Test: `financial-engine_v2/backend/tests/test_cleanup_ephemeral_sessions.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_cleanup_ephemeral_sessions.py
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

from app.services.ephemeral_sessions_store import mark_session_active, open_store
from scripts.cleanup_ephemeral_sessions import run_cleanup


def test_removes_sessions_older_than_threshold(tmp_path: Path) -> None:
    db = tmp_path / "ephem.sqlite"
    with open_store(db) as store:
        mark_session_active(store, "stale", collection_name="commentary_ephemeral_stale")
        mark_session_active(store, "fresh", collection_name="commentary_ephemeral_fresh")
        old_iso = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        store.execute(
            "UPDATE ephemeral_sessions SET last_activity_at = ? WHERE session_id='stale'",
            (old_iso,),
        )
        store.commit()

    fake_qdrant = MagicMock()
    fake_qdrant.collection_exists.return_value = True
    removed = run_cleanup(
        store_path=db, qdrant_client=fake_qdrant, older_than=timedelta(days=7)
    )
    assert removed == ["stale"]
    fake_qdrant.delete_collection.assert_called_once_with(
        collection_name="commentary_ephemeral_stale"
    )

    with open_store(db) as store:
        remaining = [r[0] for r in store.execute("SELECT session_id FROM ephemeral_sessions")]
    assert remaining == ["fresh"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_cleanup_ephemeral_sessions.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/scripts/cleanup_ephemeral_sessions.py
"""Cron-safe cleanup of stale ephemeral Qdrant collections.

Invoked by ops cron every few hours; idempotent.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.services.ephemeral_sessions_store import (
    DEFAULT_PATH,
    list_stale_sessions,
    open_store,
    remove_session,
)


def run_cleanup(
    *,
    store_path: Path = DEFAULT_PATH,
    qdrant_client,
    older_than: timedelta = timedelta(days=7),
) -> list[str]:
    removed: list[str] = []
    with open_store(store_path) as store:
        stale = list_stale_sessions(store, older_than=older_than)
        for s in stale:
            if qdrant_client.collection_exists(s.collection_name):
                qdrant_client.delete_collection(collection_name=s.collection_name)
            remove_session(store, s.session_id)
            removed.append(s.session_id)
    return removed


if __name__ == "__main__":
    from qdrant_client import QdrantClient
    import os

    qdrant = QdrantClient(url=os.environ.get("QDRANT_URL", "http://127.0.0.1:6333"))
    removed = run_cleanup(qdrant_client=qdrant)
    print(f"removed {len(removed)} stale sessions: {removed}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_cleanup_ephemeral_sessions.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/scripts/cleanup_ephemeral_sessions.py \
        financial-engine_v2/backend/tests/test_cleanup_ephemeral_sessions.py
git commit -m "milestone(youtube-ingest): ephemeral-session cleanup cron

Working: run_cleanup drops Qdrant collections + activity rows older than 7 days.
Tested: tests/test_cleanup_ephemeral_sessions.py — 1 passed."
```

---

### Task 15: Takeaways service + endpoint

**Files:**
- Create: `financial-engine_v2/backend/app/services/takeaways_service.py`
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Test: `financial-engine_v2/backend/tests/test_takeaways.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_takeaways.py
import json
import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import commentary as commentary_mod
from app.main import app
from app.services.takeaways_service import TakeawaysResult, generate_takeaways


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_generate_takeaways_shape():
    fake_router = lambda prompt, **kw: json.dumps({
        "takeaways": [
            {"text": "Bank margins compressed.", "citations": [{"chunk_id": "c1", "segment_start_seconds": 12.5}]},
        ],
        "watchlist_suggestions": [
            {"ticker": "CBA.AX", "commentary": "Margin pressure noted.", "citations": [{"chunk_id": "c1", "segment_start_seconds": 12.5}]},
        ],
        "model": "test-model",
        "prompt_version": "v1",
    })
    with patch("app.services.takeaways_service._call_router", side_effect=fake_router):
        result = generate_takeaways(
            transcript_chunks=[{"chunk_id": "c1", "text": "CBA margins fell.", "segment_start_seconds": 12.5, "segment_end_seconds": 15.0}],
            source_name="Vid",
            source_id="yt_x",
        )
    assert isinstance(result, TakeawaysResult)
    assert result.takeaways[0].text.startswith("Bank")
    assert result.watchlist_suggestions[0].ticker == "CBA.AX"
    assert result.model == "test-model"


def test_takeaways_endpoint(tmp_path: Path, monkeypatch):
    staged = tmp_path / "staged_chunks"
    staged.mkdir()
    (staged / "yt_x.jsonl").write_text(
        json.dumps({
            "chunk_id": "c1", "text": "CBA margins fell.",
            "segment_start_seconds": 12.5, "segment_end_seconds": 15.0,
            "source_id": "yt_x", "source_name": "Vid", "source_type": "youtube",
        }) + "\n"
    )
    monkeypatch.setattr(commentary_mod, "STAGED_CHUNKS_DIR", staged)
    with patch("app.api.commentary.generate_takeaways") as gen:
        gen.return_value = TakeawaysResult(
            takeaways=[], watchlist_suggestions=[],
            model="m", prompt_version="v1",
        )
        with TestClient(app) as client:
            r = client.post(
                "/api/commentary/takeaways",
                headers=_headers(),
                json={"source_id": "yt_x"},
            )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_id"] == "yt_x"
    assert "takeaways" in body
    assert "watchlist_suggestions" in body
    assert body["model"] == "m"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_takeaways.py -v`
Expected: FAIL — module + endpoint missing.

- [ ] **Step 3: Write minimal implementation**

```python
# financial-engine_v2/backend/app/services/takeaways_service.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


PROMPT_VERSION = "takeaways-v1"

_SYSTEM = """You extract investor-facing takeaways from a YouTube transcript.
Return strict JSON only with this shape:
{
  "takeaways": [{"text": "...", "citations": [{"chunk_id": "...", "segment_start_seconds": 0.0}]}],
  "watchlist_suggestions": [{"ticker": "XYZ.AX", "commentary": "...", "citations": [{"chunk_id": "...", "segment_start_seconds": 0.0}]}]
}
Rules:
- Every takeaway and suggestion MUST include at least one citation that references a chunk_id from the input.
- Only suggest ASX tickers (format XXX.AX or XXXX.AX).
- If nothing is investor-relevant, return empty arrays.
"""


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    segment_start_seconds: float


@dataclass(frozen=True)
class Takeaway:
    text: str
    citations: list[Citation]


@dataclass(frozen=True)
class WatchlistSuggestion:
    ticker: str
    commentary: str
    citations: list[Citation]


@dataclass(frozen=True)
class TakeawaysResult:
    takeaways: list[Takeaway]
    watchlist_suggestions: list[WatchlistSuggestion]
    model: str
    prompt_version: str


def _call_router(prompt: str, *, system: str = _SYSTEM) -> str:
    """Delegate to the same adaptive router /chat uses.

    Implementer note: replace with the actual router import used by
    app.routes.chat; the test monkeypatches this symbol so the exact wiring
    matters only when running the real backend.
    """
    from app.services.llm_router import complete  # real router entry point

    return complete(system=system, user=prompt)


def generate_takeaways(
    *, transcript_chunks: list[dict[str, Any]], source_name: str, source_id: str
) -> TakeawaysResult:
    prompt = _build_prompt(transcript_chunks, source_name=source_name, source_id=source_id)
    raw = _call_router(prompt)
    parsed = json.loads(raw)
    takeaways = [
        Takeaway(
            text=t["text"],
            citations=[Citation(chunk_id=c["chunk_id"], segment_start_seconds=float(c["segment_start_seconds"])) for c in t.get("citations", [])],
        )
        for t in parsed.get("takeaways", [])
    ]
    suggestions = [
        WatchlistSuggestion(
            ticker=s["ticker"],
            commentary=s["commentary"],
            citations=[Citation(chunk_id=c["chunk_id"], segment_start_seconds=float(c["segment_start_seconds"])) for c in s.get("citations", [])],
        )
        for s in parsed.get("watchlist_suggestions", [])
    ]
    return TakeawaysResult(
        takeaways=takeaways,
        watchlist_suggestions=suggestions,
        model=parsed.get("model", "unknown"),
        prompt_version=parsed.get("prompt_version", PROMPT_VERSION),
    )


def _build_prompt(chunks: list[dict[str, Any]], *, source_name: str, source_id: str) -> str:
    lines = [f"Source: {source_name} (id={source_id})", "Transcript chunks (chunk_id :: start_sec :: text):"]
    for c in chunks:
        lines.append(
            f"{c['chunk_id']} :: {c['segment_start_seconds']:.1f} :: {c['text']}"
        )
    return "\n".join(lines)
```

Add the endpoint in `app/api/commentary.py`:

```python
from app.services.takeaways_service import TakeawaysResult, generate_takeaways


class TakeawaysRequest(BaseModel):
    source_id: str


class CitationResp(BaseModel):
    chunk_id: str
    segment_start_seconds: float


class TakeawayResp(BaseModel):
    text: str
    citations: list[CitationResp]


class WatchlistSuggestionResp(BaseModel):
    ticker: str
    commentary: str
    citations: list[CitationResp]


class TakeawaysResponse(BaseModel):
    source_id: str
    takeaways: list[TakeawayResp]
    watchlist_suggestions: list[WatchlistSuggestionResp]
    model: str
    prompt_version: str


@router.post(
    "/takeaways",
    response_model=TakeawaysResponse,
    dependencies=[Depends(require_api_key)],
)
def takeaways(req: TakeawaysRequest) -> TakeawaysResponse:
    staged_file = STAGED_CHUNKS_DIR / f"{req.source_id}.jsonl"
    if not staged_file.exists():
        raise HTTPException(status_code=404, detail=f"no staged transcript: {req.source_id}")
    chunks = [json.loads(line) for line in staged_file.read_text().splitlines() if line.strip()]
    result = generate_takeaways(
        transcript_chunks=chunks,
        source_name=chunks[0].get("source_name", req.source_id),
        source_id=req.source_id,
    )
    return TakeawaysResponse(
        source_id=req.source_id,
        takeaways=[TakeawayResp(text=t.text, citations=[CitationResp(chunk_id=c.chunk_id, segment_start_seconds=c.segment_start_seconds) for c in t.citations]) for t in result.takeaways],
        watchlist_suggestions=[
            WatchlistSuggestionResp(
                ticker=s.ticker,
                commentary=s.commentary,
                citations=[CitationResp(chunk_id=c.chunk_id, segment_start_seconds=c.segment_start_seconds) for c in s.citations],
            )
            for s in result.watchlist_suggestions
        ],
        model=result.model,
        prompt_version=result.prompt_version,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_takeaways.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/takeaways_service.py \
        financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_takeaways.py
git commit -m "milestone(youtube-ingest): takeaways service + POST /takeaways

Working: generate_takeaways calls adaptive router, returns structured takeaways+watchlist suggestions with citations; endpoint wires it to staged chunks.
Tested: tests/test_takeaways.py — 2 passed."
```

---

### Task 16: GET /commentary/recent

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Test: `financial-engine_v2/backend/tests/test_commentary_recent.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_commentary_recent.py
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import commentary as commentary_mod
from app.main import app


def _headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("API_KEY", "test-key")}


def test_recent_returns_approved_only(tmp_path: Path, monkeypatch):
    registry = {
        "yt_a": {"source_name": "A", "source_type": "youtube", "approved_at": "2026-04-17T10:00:00Z"},
        "yt_b": {"source_name": "B", "source_type": "youtube", "approved_at": "2026-04-18T09:00:00Z"},
        "news_c": {"source_name": "C", "source_type": "news", "approved_at": "2026-04-18T10:00:00Z"},
        "commentary_d": {"source_name": "D", "source_type": "commentary", "approved_at": "2026-04-18T11:00:00Z"},
    }
    reg_path = tmp_path / "commentary_registry.json"
    reg_path.write_text(json.dumps(registry))
    monkeypatch.setattr(commentary_mod, "REGISTRY_PATH", reg_path)

    with TestClient(app) as client:
        r = client.get("/api/commentary/recent?limit=10", headers=_headers())
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    ids = [i["source_id"] for i in items]
    assert "news_c" not in ids  # only youtube + commentary kinds
    assert ids == ["commentary_d", "yt_b", "yt_a"]  # newest first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_recent.py -v`
Expected: FAIL — endpoint missing.

- [ ] **Step 3: Write minimal implementation**

```python
# in app/api/commentary.py
REGISTRY_PATH = Path("~/.tenn/memory/commentary_registry.json").expanduser()


class RecentItem(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    approved_at: str


class RecentResponse(BaseModel):
    items: list[RecentItem]


@router.get(
    "/recent",
    response_model=RecentResponse,
    dependencies=[Depends(require_api_key)],
)
def recent(limit: int = 20) -> RecentResponse:
    if not REGISTRY_PATH.exists():
        return RecentResponse(items=[])
    registry = json.loads(REGISTRY_PATH.read_text())
    rows = []
    for source_id, meta in registry.items():
        kind = meta.get("source_type")
        if kind not in ("youtube", "commentary"):
            continue
        rows.append(RecentItem(
            source_id=source_id,
            source_name=meta.get("source_name", source_id),
            source_type=kind,
            approved_at=meta.get("approved_at", ""),
        ))
    rows.sort(key=lambda r: r.approved_at, reverse=True)
    return RecentResponse(items=rows[:limit])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_commentary_recent.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_commentary_recent.py
git commit -m "milestone(youtube-ingest): GET /api/commentary/recent

Working: Lists approved youtube + commentary registry entries, newest first, capped by limit.
Tested: tests/test_commentary_recent.py — 1 passed."
```

---

## Phase 2 — Chat extension

Three tasks that extend the existing chat pipeline to consume attached transcripts. All paths touch `financial-engine_v2/cockpit/core/chat.py` (`tenn_chat`) and `app/routes/chat.py`.

### Task 17: ChatRequest accepts attached_sources

**Files:**
- Modify: `financial-engine_v2/backend/app/routes/chat.py`
- Test: `financial-engine_v2/backend/tests/test_chat_attached_sources_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/backend/tests/test_chat_attached_sources_schema.py
from app.routes.chat import ChatRequest


def test_chat_request_accepts_attached_sources():
    req = ChatRequest(
        session_id="sess-1",
        messages=[{"role": "user", "content": "hi"}],
        attached_sources=[
            {"source_id": "yt_a", "source_kind": "ephemeral"},
            {"source_id": "yt_b", "source_kind": "concat"},
        ],
    )
    assert req.attached_sources[0].source_id == "yt_a"
    assert req.attached_sources[0].source_kind == "ephemeral"


def test_attached_sources_defaults_empty():
    req = ChatRequest(session_id="sess-1", messages=[{"role": "user", "content": "hi"}])
    assert req.attached_sources == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2/backend && pytest tests/test_chat_attached_sources_schema.py -v`
Expected: FAIL — `attached_sources` not on model.

- [ ] **Step 3: Write minimal implementation**

In `app/routes/chat.py`, extend the `ChatRequest` pydantic model:

```python
from typing import Literal
from pydantic import BaseModel, Field


class AttachedSource(BaseModel):
    source_id: str
    source_kind: Literal["ephemeral", "concat", "primary"]


class ChatRequest(BaseModel):
    session_id: str
    messages: list[dict]
    attached_sources: list[AttachedSource] = Field(default_factory=list)
    # ...keep existing fields unchanged...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2/backend && pytest tests/test_chat_attached_sources_schema.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run existing chat tests to confirm no regression**

Run: `cd financial-engine_v2/backend && pytest tests/test_chat*.py -v`
Expected: all previously-passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/backend/app/routes/chat.py \
        financial-engine_v2/backend/tests/test_chat_attached_sources_schema.py
git commit -m "milestone(youtube-ingest): ChatRequest.attached_sources field

Working: ChatRequest accepts optional attached_sources[{source_id, source_kind}]; defaults to []; existing callers unaffected.
Tested: tests/test_chat_attached_sources_schema.py — 2 passed; prior chat tests still green."
```

---

### Task 18: tenn_chat routes attachments by source_kind

**Files:**
- Modify: `financial-engine_v2/cockpit/core/chat.py`
- Test: `financial-engine_v2/cockpit/tests/test_chat_attachment_routing.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/cockpit/tests/test_chat_attachment_routing.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from cockpit.core.chat import build_retrieval_context, CONCAT_TOKEN_THRESHOLD


def _staged_chunks(tmp: Path, source_id: str, token_count: int) -> None:
    (tmp / f"{source_id}.jsonl").write_text(
        "\n".join(
            json.dumps({
                "chunk_id": f"{source_id}_c{i}",
                "text": "word " * 5,
                "segment_start_seconds": float(i),
                "segment_end_seconds": float(i + 1),
                "source_id": source_id,
                "source_name": source_id,
                "source_type": "youtube",
            })
            for i in range(token_count // 5)
        )
    )


def test_short_attachment_concats_inline(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    _staged_chunks(tmp_path, "yt_short", token_count=400)  # well below threshold
    ctx = build_retrieval_context(
        session_id="s1",
        attached_sources=[{"source_id": "yt_short", "source_kind": "concat"}],
        query_embedding=[0.0] * 384,
        qdrant_client=MagicMock(),
    )
    assert any("word word" in seg.text for seg in ctx.concat_segments)
    assert ctx.ephemeral_hits == []


def test_long_attachment_uses_ephemeral_search(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    _staged_chunks(tmp_path, "yt_long", token_count=CONCAT_TOKEN_THRESHOLD + 500)

    fake_client = MagicMock()
    fake_client.search.return_value = [
        MagicMock(payload={"text": "hit text", "source_id": "yt_long", "source_kind": "ephemeral", "segment_start_seconds": 42.0, "source_name": "Long"}, score=0.9, id="yt_long_c1"),
    ]
    ctx = build_retrieval_context(
        session_id="s1",
        attached_sources=[{"source_id": "yt_long", "source_kind": "ephemeral"}],
        query_embedding=[0.0] * 384,
        qdrant_client=fake_client,
    )
    assert ctx.concat_segments == []
    assert len(ctx.ephemeral_hits) == 1
    assert ctx.ephemeral_hits[0].source_kind == "ephemeral"


def test_activity_mark_on_ephemeral_use(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("cockpit.core.chat.STAGED_CHUNKS_DIR", tmp_path)
    _staged_chunks(tmp_path, "yt_long", token_count=CONCAT_TOKEN_THRESHOLD + 500)

    fake_client = MagicMock()
    fake_client.search.return_value = []
    with patch("cockpit.core.chat.mark_session_active") as mock_mark:
        build_retrieval_context(
            session_id="s1",
            attached_sources=[{"source_id": "yt_long", "source_kind": "ephemeral"}],
            query_embedding=[0.0] * 384,
            qdrant_client=fake_client,
        )
    mock_mark.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2 && pytest cockpit/tests/test_chat_attachment_routing.py -v`
Expected: FAIL — `build_retrieval_context`/`CONCAT_TOKEN_THRESHOLD` not defined.

- [ ] **Step 3: Write minimal implementation**

In `financial-engine_v2/cockpit/core/chat.py`, add a new `build_retrieval_context` function that the existing chat pipeline calls before prompt assembly. Keep prior context-building untouched — route attached sources through the new function and merge its output into the existing retrieval flow.

```python
# Additions near the top of chat.py
from dataclasses import dataclass, field
from pathlib import Path

from app.services.commentary_ephemeral import search_chunks as ephemeral_search
from app.services.ephemeral_sessions_store import mark_session_active, open_store


STAGED_CHUNKS_DIR = Path("~/.tenn/memory/staged_chunks").expanduser()
CONCAT_TOKEN_THRESHOLD = 4000  # internal tunable, not part of public API


@dataclass(frozen=True)
class ConcatSegment:
    source_id: str
    source_name: str
    text: str
    segment_start_seconds: float


@dataclass(frozen=True)
class EphemeralHit:
    source_id: str
    source_name: str
    chunk_id: str
    text: str
    segment_start_seconds: float
    source_kind: str  # "ephemeral"
    score: float


@dataclass(frozen=True)
class RetrievalContext:
    concat_segments: list[ConcatSegment] = field(default_factory=list)
    ephemeral_hits: list[EphemeralHit] = field(default_factory=list)


def _approx_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def _load_staged(source_id: str) -> list[dict]:
    p = STAGED_CHUNKS_DIR / f"{source_id}.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def build_retrieval_context(
    *,
    session_id: str,
    attached_sources: list[dict],
    query_embedding: list[float],
    qdrant_client,
) -> RetrievalContext:
    concat_segments: list[ConcatSegment] = []
    ephemeral_hits: list[EphemeralHit] = []
    touched_ephemeral = False

    for att in attached_sources:
        sid = att["source_id"]
        kind = att["source_kind"]
        chunks = _load_staged(sid)
        total_tokens = sum(_approx_token_count(c["text"]) for c in chunks)

        if kind == "concat" or (kind != "ephemeral" and total_tokens < CONCAT_TOKEN_THRESHOLD):
            for c in chunks:
                concat_segments.append(
                    ConcatSegment(
                        source_id=sid,
                        source_name=c.get("source_name", sid),
                        text=c["text"],
                        segment_start_seconds=float(c["segment_start_seconds"]),
                    )
                )
            continue

        # ephemeral path
        touched_ephemeral = True
        hits = ephemeral_search(
            qdrant_client, session_id, query_vector=query_embedding, limit=5
        )
        for h in hits:
            payload = h.payload or {}
            ephemeral_hits.append(
                EphemeralHit(
                    source_id=payload.get("source_id", sid),
                    source_name=payload.get("source_name", sid),
                    chunk_id=str(h.id),
                    text=payload.get("text", ""),
                    segment_start_seconds=float(payload.get("segment_start_seconds", 0.0)),
                    source_kind=payload.get("source_kind", "ephemeral"),
                    score=float(getattr(h, "score", 0.0)),
                )
            )

    if touched_ephemeral:
        with open_store() as store:
            mark_session_active(
                store,
                session_id,
                collection_name=f"commentary_ephemeral_{session_id}",
            )

    return RetrievalContext(
        concat_segments=concat_segments, ephemeral_hits=ephemeral_hits
    )
```

Wire `build_retrieval_context` into the existing `tenn_chat`/orchestrator entrypoint so that `attached_sources` from `ChatRequest` flows through. The caller should merge `concat_segments` into the system prompt and feed `ephemeral_hits` into the same citation/source list already used for news results.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2 && pytest cockpit/tests/test_chat_attachment_routing.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run existing cockpit chat tests to confirm no regression**

Run: `cd financial-engine_v2 && pytest cockpit/tests/ -v`
Expected: all previously-passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/core/chat.py \
        financial-engine_v2/cockpit/tests/test_chat_attachment_routing.py
git commit -m "milestone(youtube-ingest): attachment-aware retrieval routing

Working: build_retrieval_context concats short transcripts, searches ephemeral Qdrant for long ones, and marks session active on every ephemeral use.
Tested: cockpit/tests/test_chat_attachment_routing.py — 3 passed; existing cockpit tests green."
```

---

### Task 19: Citations carry source_kind; scorer excludes ephemeral from primary reranking

**Files:**
- Modify: `financial-engine_v2/cockpit/core/chat.py`
- Test: `financial-engine_v2/cockpit/tests/test_chat_source_kind_separation.py`

- [ ] **Step 1: Write the failing test**

```python
# financial-engine_v2/cockpit/tests/test_chat_source_kind_separation.py
from cockpit.core.chat import (
    assemble_citations,
    filter_for_primary_reranking,
    EphemeralHit,
    ConcatSegment,
)


def test_assembled_citations_preserve_source_kind():
    concat = [ConcatSegment(source_id="yt_a", source_name="A", text="t", segment_start_seconds=1.0)]
    ephem = [EphemeralHit(source_id="yt_b", source_name="B", chunk_id="c1", text="t2", segment_start_seconds=2.0, source_kind="ephemeral", score=0.9)]
    primary = [{"source_id": "doc_x", "text": "primary", "source_kind": "primary"}]

    cits = assemble_citations(concat_segments=concat, ephemeral_hits=ephem, primary_hits=primary)
    kinds = {c["source_kind"] for c in cits}
    assert kinds == {"concat", "ephemeral", "primary"}


def test_primary_reranker_ignores_ephemeral_and_concat():
    hits = [
        {"source_id": "doc_x", "source_kind": "primary", "score": 0.8},
        {"source_id": "yt_a", "source_kind": "ephemeral", "score": 0.95},
        {"source_id": "yt_b", "source_kind": "concat", "score": 0.91},
    ]
    filtered = filter_for_primary_reranking(hits)
    assert [h["source_id"] for h in filtered] == ["doc_x"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd financial-engine_v2 && pytest cockpit/tests/test_chat_source_kind_separation.py -v`
Expected: FAIL — helpers missing.

- [ ] **Step 3: Write minimal implementation**

Add to `cockpit/core/chat.py`:

```python
def assemble_citations(
    *,
    concat_segments: list[ConcatSegment],
    ephemeral_hits: list[EphemeralHit],
    primary_hits: list[dict],
) -> list[dict]:
    cits: list[dict] = []
    for c in concat_segments:
        cits.append({
            "source_id": c.source_id,
            "source_name": c.source_name,
            "text": c.text,
            "segment_start_seconds": c.segment_start_seconds,
            "source_kind": "concat",
        })
    for h in ephemeral_hits:
        cits.append({
            "source_id": h.source_id,
            "source_name": h.source_name,
            "chunk_id": h.chunk_id,
            "text": h.text,
            "segment_start_seconds": h.segment_start_seconds,
            "source_kind": h.source_kind,  # "ephemeral"
            "score": h.score,
        })
    for p in primary_hits:
        cits.append({**p, "source_kind": p.get("source_kind", "primary")})
    return cits


def filter_for_primary_reranking(hits: list[dict]) -> list[dict]:
    """Keep only primary hits so the learning loop isn't polluted by ephemeral/concat attachments."""
    return [h for h in hits if h.get("source_kind") == "primary"]
```

Ensure the existing reranker/feedback loop calls `filter_for_primary_reranking` before scoring or persisting feedback.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd financial-engine_v2 && pytest cockpit/tests/test_chat_source_kind_separation.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/cockpit/core/chat.py \
        financial-engine_v2/cockpit/tests/test_chat_source_kind_separation.py
git commit -m "milestone(youtube-ingest): source_kind citation tagging + learning-loop shield

Working: Citations tagged concat/ephemeral/primary; primary reranking excludes ephemeral+concat to prevent feedback-loop pollution.
Tested: cockpit/tests/test_chat_source_kind_separation.py — 2 passed."
```

---

## Phase 3 — Cockpit-ui proxy routes

Six proxy-route tasks, all following the template at `cockpit-ui/app/api/cockpit/action/execute/route.ts` (nodejs runtime, `copyRequestHeaders`, `NEXT_PUBLIC_API_URL` resolution, 15-minute timeout for LLM-bound calls, 60-second for quick ones). Every proxy forwards `X-API-Key` and returns the backend body verbatim on success.

### Task 20: POST /api/cockpit/commentary/ingest-url proxy

**Files:**
- Create: `cockpit-ui/app/api/cockpit/commentary/ingest-url/route.ts`

- [ ] **Step 1: Write the failing test skipped — Playwright integration covers this later**

(Proxy routes are covered by the Playwright tests in Phase 5; a dedicated unit test for each proxy would duplicate coverage. Skip the RED/GREEN cycle here and keep the implementer honest with a smoke `curl` after.)

- [ ] **Step 2: Write the implementation**

```typescript
// cockpit-ui/app/api/cockpit/commentary/ingest-url/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 120

const INGEST_TIMEOUT_MS = 2 * 60 * 1000

export async function POST(request: NextRequest): Promise<NextResponse> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), INGEST_TIMEOUT_MS)
  try {
    const body = await request.text()
    const backend = await fetch(`${resolveBackendUrl()}/api/commentary/ingest-url`, {
      method: 'POST',
      headers: copyRequestHeaders(request),
      body,
      signal: controller.signal,
    })
    const payload = await backend.text()
    return new NextResponse(payload, {
      status: backend.status,
      headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
    })
  } finally {
    clearTimeout(timer)
  }
}
```

If `@/lib/proxy` does not yet export `copyRequestHeaders`/`resolveBackendUrl`, copy the inline helpers from `cockpit-ui/app/api/cockpit/action/execute/route.ts` verbatim — do not introduce a new abstraction solely for these tasks.

- [ ] **Step 3: Smoke test**

```bash
# with backend running on :8000
curl -s -X POST http://127.0.0.1:3000/api/cockpit/commentary/ingest-url \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ"}'
```

Expected: 200 with `source_id`, `title`, `chunk_count`, `detected_tickers`, `status`.

- [ ] **Step 4: Commit**

```bash
git add cockpit-ui/app/api/cockpit/commentary/ingest-url/route.ts
git commit -m "milestone(youtube-ingest): cockpit-ui ingest-url proxy

Working: POST /api/cockpit/commentary/ingest-url forwards to backend with X-API-Key and 2-min timeout.
Tested: curl smoke test returns 200 with source_id/title/status=pending."
```

---

### Task 21: Transcripts GET proxy

**Files:**
- Create: `cockpit-ui/app/api/cockpit/commentary/transcripts/[sourceId]/route.ts`

- [ ] **Step 1: Write the implementation**

```typescript
// cockpit-ui/app/api/cockpit/commentary/transcripts/[sourceId]/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 60

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ sourceId: string }> },
): Promise<NextResponse> {
  const { sourceId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/commentary/transcripts/${encodeURIComponent(sourceId)}`,
    { headers: copyRequestHeaders(request) },
  )
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
  })
}
```

- [ ] **Step 2: Smoke test**

```bash
curl -s http://127.0.0.1:3000/api/cockpit/commentary/transcripts/yt_abc123 \
  -H "X-API-Key: $API_KEY"
```

Expected: 200 with `source_id`, `status`, `chunks[]`; 404 when unknown.

- [ ] **Step 3: Commit**

```bash
git add cockpit-ui/app/api/cockpit/commentary/transcripts/*
git commit -m "milestone(youtube-ingest): cockpit-ui transcripts GET proxy

Working: GET /api/cockpit/commentary/transcripts/[sourceId] forwards to backend.
Tested: curl smoke — 200 for known, 404 for unknown."
```

---

### Task 22: Takeaways proxy

**Files:**
- Create: `cockpit-ui/app/api/cockpit/commentary/takeaways/route.ts`

- [ ] **Step 1: Write the implementation**

```typescript
// cockpit-ui/app/api/cockpit/commentary/takeaways/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 900

const TAKEAWAYS_TIMEOUT_MS = 15 * 60 * 1000

export async function POST(request: NextRequest): Promise<NextResponse> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TAKEAWAYS_TIMEOUT_MS)
  try {
    const body = await request.text()
    const backend = await fetch(`${resolveBackendUrl()}/api/commentary/takeaways`, {
      method: 'POST',
      headers: copyRequestHeaders(request),
      body,
      signal: controller.signal,
    })
    const payload = await backend.text()
    return new NextResponse(payload, {
      status: backend.status,
      headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
    })
  } finally {
    clearTimeout(timer)
  }
}
```

- [ ] **Step 2: Smoke test**

```bash
curl -s -X POST http://127.0.0.1:3000/api/cockpit/commentary/takeaways \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"source_id":"yt_abc123"}'
```

Expected: 200 with `takeaways[]`, `watchlist_suggestions[]`, `model`, `prompt_version`.

- [ ] **Step 3: Commit**

```bash
git add cockpit-ui/app/api/cockpit/commentary/takeaways/route.ts
git commit -m "milestone(youtube-ingest): cockpit-ui takeaways proxy

Working: POST /api/cockpit/commentary/takeaways forwards with 15-min LLM timeout.
Tested: curl smoke returns 200 with takeaways + watchlist_suggestions."
```

---

### Task 23: Ephemeral-index POST + DELETE proxies

**Files:**
- Create: `cockpit-ui/app/api/cockpit/commentary/ephemeral-index/route.ts`
- Create: `cockpit-ui/app/api/cockpit/commentary/ephemeral-index/[sessionId]/route.ts`

- [ ] **Step 1: Write POST handler**

```typescript
// cockpit-ui/app/api/cockpit/commentary/ephemeral-index/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 300

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text()
  const backend = await fetch(`${resolveBackendUrl()}/api/commentary/ephemeral-index`, {
    method: 'POST',
    headers: copyRequestHeaders(request),
    body,
  })
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
  })
}
```

- [ ] **Step 2: Write DELETE handler**

```typescript
// cockpit-ui/app/api/cockpit/commentary/ephemeral-index/[sessionId]/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 60

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
): Promise<NextResponse> {
  const { sessionId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/commentary/ephemeral-index/${encodeURIComponent(sessionId)}`,
    { method: 'DELETE', headers: copyRequestHeaders(request) },
  )
  return new NextResponse(null, { status: backend.status })
}
```

- [ ] **Step 3: Smoke test**

```bash
curl -s -X POST http://127.0.0.1:3000/api/cockpit/commentary/ephemeral-index \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"session_id":"test-s1","source_ids":["yt_abc123"]}'

curl -s -X DELETE http://127.0.0.1:3000/api/cockpit/commentary/ephemeral-index/test-s1 \
  -H "X-API-Key: $API_KEY"
```

Expected: POST returns 200 with `indexed_chunks`, DELETE returns 204.

- [ ] **Step 4: Commit**

```bash
git add cockpit-ui/app/api/cockpit/commentary/ephemeral-index/
git commit -m "milestone(youtube-ingest): cockpit-ui ephemeral-index proxies

Working: POST builds per-session Qdrant collection; DELETE tears it down; both forward X-API-Key.
Tested: curl POST=200, DELETE=204."
```

---

### Task 24: Recent proxy

**Files:**
- Create: `cockpit-ui/app/api/cockpit/commentary/recent/route.ts`

- [ ] **Step 1: Write the implementation**

```typescript
// cockpit-ui/app/api/cockpit/commentary/recent/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(request: NextRequest): Promise<NextResponse> {
  const url = new URL(request.url)
  const backend = await fetch(
    `${resolveBackendUrl()}/api/commentary/recent?${url.searchParams.toString()}`,
    { headers: copyRequestHeaders(request) },
  )
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
  })
}
```

- [ ] **Step 2: Smoke test**

```bash
curl -s "http://127.0.0.1:3000/api/cockpit/commentary/recent?limit=5" \
  -H "X-API-Key: $API_KEY"
```

Expected: 200 with `items[]` sorted newest first.

- [ ] **Step 3: Commit**

```bash
git add cockpit-ui/app/api/cockpit/commentary/recent/route.ts
git commit -m "milestone(youtube-ingest): cockpit-ui recent proxy

Working: GET forwards limit query param to backend.
Tested: curl returns sorted items[]."
```

---

### Task 25: Watchlist POST/GET/DELETE proxies

**Files:**
- Create: `cockpit-ui/app/api/cockpit/watchlist/route.ts`
- Create: `cockpit-ui/app/api/cockpit/watchlist/[ticker]/route.ts`

- [ ] **Step 1: Write POST + GET**

```typescript
// cockpit-ui/app/api/cockpit/watchlist/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text()
  const backend = await fetch(`${resolveBackendUrl()}/api/watchlist`, {
    method: 'POST',
    headers: copyRequestHeaders(request),
    body,
  })
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
  })
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const backend = await fetch(`${resolveBackendUrl()}/api/watchlist`, {
    headers: copyRequestHeaders(request),
  })
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: { 'Content-Type': backend.headers.get('Content-Type') ?? 'application/json' },
  })
}
```

- [ ] **Step 2: Write DELETE**

```typescript
// cockpit-ui/app/api/cockpit/watchlist/[ticker]/route.ts
import { NextRequest, NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ ticker: string }> },
): Promise<NextResponse> {
  const { ticker } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/watchlist/${encodeURIComponent(ticker)}`,
    { method: 'DELETE', headers: copyRequestHeaders(request) },
  )
  return new NextResponse(null, { status: backend.status })
}
```

- [ ] **Step 3: Smoke test**

```bash
curl -s -X POST http://127.0.0.1:3000/api/cockpit/watchlist \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"ticker":"CBA.AX","note":"test","stance":"watch"}'
curl -s http://127.0.0.1:3000/api/cockpit/watchlist -H "X-API-Key: $API_KEY"
curl -s -X DELETE http://127.0.0.1:3000/api/cockpit/watchlist/CBA.AX -H "X-API-Key: $API_KEY"
```

Expected: 201, 200 with items, 204. Duplicate POST returns 409.

- [ ] **Step 4: Commit**

```bash
git add cockpit-ui/app/api/cockpit/watchlist/
git commit -m "milestone(youtube-ingest): cockpit-ui watchlist proxies

Working: POST/GET/DELETE forward to /api/watchlist; preserve 409 on duplicate.
Tested: curl add/list/remove cycle succeeds; duplicate returns 409."
```

---

## Phase 4 — Cockpit-ui components

Nine tasks. Component tests run under Vitest (added in Task 26). Existing codebase uses Playwright only — do not replace Playwright; add Vitest alongside it.

### Task 26: Install and configure Vitest

**Files:**
- Modify: `cockpit-ui/package.json`
- Create: `cockpit-ui/vitest.config.ts`
- Create: `cockpit-ui/vitest.setup.ts`
- Modify: `cockpit-ui/tsconfig.json` (only if types field needs update)

- [ ] **Step 1: Install dependencies**

```bash
cd cockpit-ui
pnpm add -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 2: Write `vitest.config.ts`**

```typescript
// cockpit-ui/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    include: ['components/**/*.test.{ts,tsx}', 'lib/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
})
```

- [ ] **Step 3: Write `vitest.setup.ts`**

```typescript
// cockpit-ui/vitest.setup.ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: Add script to `package.json`**

```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest"
}
```

(Keep existing scripts. Do not remove the Playwright commands.)

- [ ] **Step 5: Write a smoke test to confirm Vitest runs**

```typescript
// cockpit-ui/lib/__smoke__/vitest.test.ts
import { describe, expect, it } from 'vitest'

describe('vitest smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 6: Run smoke test**

Run: `cd cockpit-ui && pnpm test`
Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add cockpit-ui/package.json cockpit-ui/pnpm-lock.yaml \
        cockpit-ui/vitest.config.ts cockpit-ui/vitest.setup.ts \
        cockpit-ui/lib/__smoke__/vitest.test.ts
git commit -m "milestone(youtube-ingest): vitest scaffolding

Working: pnpm test runs Vitest with jsdom + testing-library; smoke test passes.
Tested: lib/__smoke__/vitest.test.ts — 1 passed."
```

---

### Task 27: Attachments state hook

**Files:**
- Create: `cockpit-ui/lib/hooks/use-attached-sources.ts`
- Test: `cockpit-ui/lib/hooks/use-attached-sources.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// cockpit-ui/lib/hooks/use-attached-sources.test.ts
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useAttachedSources } from './use-attached-sources'

describe('useAttachedSources', () => {
  it('attaches and detaches sources', () => {
    const { result } = renderHook(() => useAttachedSources())
    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'ephemeral', title: 'A' })
    })
    expect(result.current.attached).toHaveLength(1)
    expect(result.current.attached[0].sourceId).toBe('yt_a')

    act(() => {
      result.current.detach('yt_a')
    })
    expect(result.current.attached).toHaveLength(0)
  })

  it('dedupes repeat attaches on same source_id', () => {
    const { result } = renderHook(() => useAttachedSources())
    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'concat', title: 'A' })
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'ephemeral', title: 'A' })
    })
    expect(result.current.attached).toHaveLength(1)
    // later attach wins for kind
    expect(result.current.attached[0].sourceKind).toBe('ephemeral')
  })

  it('serializes to ChatRequest shape', () => {
    const { result } = renderHook(() => useAttachedSources())
    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'concat', title: 'A' })
    })
    expect(result.current.serialize()).toEqual([
      { source_id: 'yt_a', source_kind: 'concat' },
    ])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test`
Expected: FAIL — hook does not exist.

- [ ] **Step 3: Write the implementation**

```typescript
// cockpit-ui/lib/hooks/use-attached-sources.ts
import { useCallback, useState } from 'react'

export type AttachedSourceKind = 'ephemeral' | 'concat' | 'primary'

export interface AttachedSource {
  sourceId: string
  sourceKind: AttachedSourceKind
  title: string
}

export interface UseAttachedSources {
  attached: AttachedSource[]
  attach: (source: AttachedSource) => void
  detach: (sourceId: string) => void
  clear: () => void
  serialize: () => Array<{ source_id: string; source_kind: AttachedSourceKind }>
}

export function useAttachedSources(): UseAttachedSources {
  const [attached, setAttached] = useState<AttachedSource[]>([])

  const attach = useCallback((source: AttachedSource) => {
    setAttached((prev) => {
      const others = prev.filter((s) => s.sourceId !== source.sourceId)
      return [...others, source]
    })
  }, [])

  const detach = useCallback((sourceId: string) => {
    setAttached((prev) => prev.filter((s) => s.sourceId !== sourceId))
  }, [])

  const clear = useCallback(() => setAttached([]), [])

  const serialize = useCallback(
    () =>
      attached.map((s) => ({
        source_id: s.sourceId,
        source_kind: s.sourceKind,
      })),
    [attached],
  )

  return { attached, attach, detach, clear, serialize }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test lib/hooks/use-attached-sources.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/lib/hooks/use-attached-sources.ts \
        cockpit-ui/lib/hooks/use-attached-sources.test.ts
git commit -m "milestone(youtube-ingest): useAttachedSources hook

Working: Attach/detach/clear/serialize with dedupe-by-source_id (last write wins on sourceKind).
Tested: lib/hooks/use-attached-sources.test.ts — 3 passed."
```

---

### Task 28: URL paste detection utility

**Files:**
- Create: `cockpit-ui/lib/youtube-url.ts`
- Test: `cockpit-ui/lib/youtube-url.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// cockpit-ui/lib/youtube-url.test.ts
import { describe, expect, it } from 'vitest'

import { extractYouTubeUrl, isYouTubeUrl } from './youtube-url'

describe('YouTube URL detection', () => {
  it('accepts canonical formats', () => {
    expect(isYouTubeUrl('https://youtu.be/abc123')).toBe(true)
    expect(isYouTubeUrl('https://www.youtube.com/watch?v=abc123')).toBe(true)
    expect(isYouTubeUrl('https://youtube.com/shorts/abc123')).toBe(true)
  })

  it('rejects unrelated URLs', () => {
    expect(isYouTubeUrl('https://example.com')).toBe(false)
    expect(isYouTubeUrl('not a url at all')).toBe(false)
  })

  it('extracts URL from surrounding text', () => {
    const hit = extractYouTubeUrl('check this https://youtu.be/abc123 now')
    expect(hit).toBe('https://youtu.be/abc123')
  })

  it('returns null when no URL present', () => {
    expect(extractYouTubeUrl('just text')).toBe(null)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test lib/youtube-url.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the implementation**

```typescript
// cockpit-ui/lib/youtube-url.ts
const YOUTUBE_URL_RE =
  /https?:\/\/(?:www\.)?(?:youtu\.be\/[A-Za-z0-9_-]{6,}|youtube\.com\/(?:watch\?v=[A-Za-z0-9_-]{6,}|shorts\/[A-Za-z0-9_-]{6,}))[^\s]*/i

export function isYouTubeUrl(input: string): boolean {
  return YOUTUBE_URL_RE.test(input.trim())
}

export function extractYouTubeUrl(input: string): string | null {
  const match = input.match(YOUTUBE_URL_RE)
  return match ? match[0] : null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test lib/youtube-url.test.ts`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/lib/youtube-url.ts cockpit-ui/lib/youtube-url.test.ts
git commit -m "milestone(youtube-ingest): YouTube URL detection utility

Working: isYouTubeUrl / extractYouTubeUrl handle youtu.be, watch?v=, shorts formats with surrounding text.
Tested: lib/youtube-url.test.ts — 4 passed."
```

---

### Task 29: IngestSummaryCard component

**Files:**
- Create: `cockpit-ui/components/cockpit/chat/ingest-summary-card.tsx`
- Test: `cockpit-ui/components/cockpit/chat/ingest-summary-card.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// cockpit-ui/components/cockpit/chat/ingest-summary-card.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { IngestSummaryCard } from './ingest-summary-card'

describe('IngestSummaryCard', () => {
  const summary = {
    sourceId: 'yt_abc',
    title: 'CBA Results Review',
    chunkCount: 12,
    detectedTickers: ['CBA.AX', 'BHP.AX'],
    status: 'pending' as const,
  }

  it('renders title, chunk count, tickers', () => {
    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={false}
        onAttach={() => {}}
        onDetach={() => {}}
        onAddTicker={() => {}}
      />,
    )
    expect(screen.getByText(/CBA Results Review/)).toBeInTheDocument()
    expect(screen.getByText(/12 chunks/)).toBeInTheDocument()
    expect(screen.getByText('CBA.AX')).toBeInTheDocument()
    expect(screen.getByText('BHP.AX')).toBeInTheDocument()
  })

  it('calls onAttach when Attach clicked', async () => {
    const onAttach = vi.fn()
    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={false}
        onAttach={onAttach}
        onDetach={() => {}}
        onAddTicker={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /attach/i }))
    expect(onAttach).toHaveBeenCalledWith('yt_abc')
  })

  it('swaps Attach for Detach when isAttached', async () => {
    const onDetach = vi.fn()
    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={true}
        onAttach={() => {}}
        onDetach={onDetach}
        onAddTicker={() => {}}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /detach/i }))
    expect(onDetach).toHaveBeenCalledWith('yt_abc')
  })

  it('calls onAddTicker with ticker when Add clicked', async () => {
    const onAddTicker = vi.fn()
    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={true}
        onAttach={() => {}}
        onDetach={() => {}}
        onAddTicker={onAddTicker}
      />,
    )
    await userEvent.click(screen.getAllByRole('button', { name: /add to watchlist/i })[0])
    expect(onAddTicker).toHaveBeenCalledWith('CBA.AX')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/ingest-summary-card.test.tsx`
Expected: FAIL — component missing.

- [ ] **Step 3: Write the implementation**

```tsx
// cockpit-ui/components/cockpit/chat/ingest-summary-card.tsx
'use client'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export interface IngestSummary {
  sourceId: string
  title: string
  chunkCount: number
  detectedTickers: string[]
  status: 'pending' | 'approved'
}

interface IngestSummaryCardProps {
  summary: IngestSummary
  isAttached: boolean
  onAttach: (sourceId: string) => void
  onDetach: (sourceId: string) => void
  onAddTicker: (ticker: string) => void
}

export function IngestSummaryCard({
  summary,
  isAttached,
  onAttach,
  onDetach,
  onAddTicker,
}: IngestSummaryCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium truncate">{summary.title}</div>
          <div className="text-xs text-muted-foreground">
            {summary.chunkCount} chunks • status: {summary.status}
          </div>
        </div>
        {isAttached ? (
          <Button size="sm" variant="outline" onClick={() => onDetach(summary.sourceId)}>
            Detach
          </Button>
        ) : (
          <Button size="sm" onClick={() => onAttach(summary.sourceId)}>
            Attach
          </Button>
        )}
      </div>

      {summary.detectedTickers.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Detected tickers:</span>
          {summary.detectedTickers.map((ticker) => (
            <span key={ticker} className="flex items-center gap-1">
              <Badge variant="secondary">{ticker}</Badge>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onAddTicker(ticker)}
                aria-label={`Add ${ticker} to watchlist`}
              >
                + add to watchlist
              </Button>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/ingest-summary-card.test.tsx`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/components/cockpit/chat/ingest-summary-card.tsx \
        cockpit-ui/components/cockpit/chat/ingest-summary-card.test.tsx
git commit -m "milestone(youtube-ingest): IngestSummaryCard

Working: Shows title, chunk count, detected tickers; Attach/Detach toggles; Add-to-watchlist per ticker.
Tested: ingest-summary-card.test.tsx — 4 passed."
```

---

### Task 30: TakeawaysPanel component

**Files:**
- Create: `cockpit-ui/components/cockpit/chat/takeaways-panel.tsx`
- Test: `cockpit-ui/components/cockpit/chat/takeaways-panel.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// cockpit-ui/components/cockpit/chat/takeaways-panel.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TakeawaysPanel } from './takeaways-panel'

describe('TakeawaysPanel', () => {
  const payload = {
    sourceId: 'yt_abc',
    videoId: 'abc',
    takeaways: [
      {
        text: 'Bank margins compressed.',
        citations: [{ chunkId: 'c1', segmentStartSeconds: 12.5 }],
      },
    ],
    watchlistSuggestions: [
      {
        ticker: 'CBA.AX',
        commentary: 'Margin pressure noted in Q3.',
        citations: [{ chunkId: 'c1', segmentStartSeconds: 12.5 }],
      },
    ],
    model: 'llama-3',
    promptVersion: 'takeaways-v1',
  }

  it('renders takeaways with citation buttons', () => {
    render(<TakeawaysPanel payload={payload} onAddTicker={() => {}} onJumpToCitation={() => {}} />)
    expect(screen.getByText(/Bank margins compressed/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /0:12/ })).toBeInTheDocument()
  })

  it('renders watchlist suggestions with Add button', async () => {
    const onAddTicker = vi.fn()
    render(<TakeawaysPanel payload={payload} onAddTicker={onAddTicker} onJumpToCitation={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /add CBA\.AX/i }))
    expect(onAddTicker).toHaveBeenCalledWith({
      ticker: 'CBA.AX',
      commentary: 'Margin pressure noted in Q3.',
      sourceId: 'yt_abc',
    })
  })

  it('emits citation click', async () => {
    const onJump = vi.fn()
    render(<TakeawaysPanel payload={payload} onAddTicker={() => {}} onJumpToCitation={onJump} />)
    await userEvent.click(screen.getByRole('button', { name: /0:12/ }))
    expect(onJump).toHaveBeenCalledWith({ chunkId: 'c1', segmentStartSeconds: 12.5 })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/takeaways-panel.test.tsx`
Expected: FAIL — component missing.

- [ ] **Step 3: Write the implementation**

```tsx
// cockpit-ui/components/cockpit/chat/takeaways-panel.tsx
'use client'

import { Button } from '@/components/ui/button'

export interface TakeawayCitation {
  chunkId: string
  segmentStartSeconds: number
}

export interface Takeaway {
  text: string
  citations: TakeawayCitation[]
}

export interface WatchlistSuggestion {
  ticker: string
  commentary: string
  citations: TakeawayCitation[]
}

export interface TakeawaysPayload {
  sourceId: string
  videoId: string
  takeaways: Takeaway[]
  watchlistSuggestions: WatchlistSuggestion[]
  model: string
  promptVersion: string
}

interface TakeawaysPanelProps {
  payload: TakeawaysPayload
  onAddTicker: (input: { ticker: string; commentary: string; sourceId: string }) => void
  onJumpToCitation: (citation: TakeawayCitation) => void
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function TakeawaysPanel({ payload, onAddTicker, onJumpToCitation }: TakeawaysPanelProps) {
  return (
    <div className="space-y-4">
      <section>
        <h3 className="text-sm font-medium mb-2">Takeaways</h3>
        <ul className="space-y-2">
          {payload.takeaways.map((t, idx) => (
            <li key={idx} className="text-sm">
              <span>{t.text}</span>
              {t.citations.map((c) => (
                <Button
                  key={`${c.chunkId}-${c.segmentStartSeconds}`}
                  size="sm"
                  variant="ghost"
                  className="ml-1 h-6 px-2 text-xs"
                  onClick={() => onJumpToCitation(c)}
                  aria-label={`jump to ${formatTimestamp(c.segmentStartSeconds)}`}
                >
                  ▶ {formatTimestamp(c.segmentStartSeconds)}
                </Button>
              ))}
            </li>
          ))}
        </ul>
      </section>

      {payload.watchlistSuggestions.length > 0 ? (
        <section>
          <h3 className="text-sm font-medium mb-2">Watchlist suggestions</h3>
          <ul className="space-y-2">
            {payload.watchlistSuggestions.map((s) => (
              <li key={s.ticker} className="flex items-start justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <div className="font-medium">{s.ticker}</div>
                  <div className="text-muted-foreground">{s.commentary}</div>
                </div>
                <Button
                  size="sm"
                  aria-label={`add ${s.ticker} to watchlist`}
                  onClick={() =>
                    onAddTicker({
                      ticker: s.ticker,
                      commentary: s.commentary,
                      sourceId: payload.sourceId,
                    })
                  }
                >
                  Add
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="text-[11px] text-muted-foreground">
        model: {payload.model} • prompt: {payload.promptVersion}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/takeaways-panel.test.tsx`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/components/cockpit/chat/takeaways-panel.tsx \
        cockpit-ui/components/cockpit/chat/takeaways-panel.test.tsx
git commit -m "milestone(youtube-ingest): TakeawaysPanel

Working: Renders takeaways + watchlist suggestions with MM:SS citation buttons and ticker Add actions.
Tested: takeaways-panel.test.tsx — 3 passed."
```

---

### Task 31: SourcesDrawer with Recent list

**Files:**
- Create: `cockpit-ui/components/cockpit/chat/sources-drawer.tsx`
- Test: `cockpit-ui/components/cockpit/chat/sources-drawer.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// cockpit-ui/components/cockpit/chat/sources-drawer.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { SourcesDrawer } from './sources-drawer'

describe('SourcesDrawer', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches /api/cockpit/commentary/recent when opened', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          { source_id: 'yt_a', source_name: 'Video A', source_type: 'youtube', approved_at: '2026-04-18T10:00:00Z' },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<SourcesDrawer open apiKey="k" onReattach={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('Video A')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/commentary/recent?limit=20',
      expect.objectContaining({ headers: expect.objectContaining({ 'X-API-Key': 'k' }) }),
    )
  })

  it('emits onReattach on item click', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            { source_id: 'yt_a', source_name: 'Video A', source_type: 'youtube', approved_at: '2026-04-18T10:00:00Z' },
          ],
        }),
      }),
    )
    const onReattach = vi.fn()
    render(<SourcesDrawer open apiKey="k" onReattach={onReattach} onClose={() => {}} />)
    await waitFor(() => screen.getByText('Video A'))
    await userEvent.click(screen.getByRole('button', { name: /re-?attach Video A/i }))
    expect(onReattach).toHaveBeenCalledWith({ sourceId: 'yt_a', title: 'Video A' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/sources-drawer.test.tsx`
Expected: FAIL — component missing.

- [ ] **Step 3: Write the implementation**

```tsx
// cockpit-ui/components/cockpit/chat/sources-drawer.tsx
'use client'

import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'

interface RecentItem {
  source_id: string
  source_name: string
  source_type: string
  approved_at: string
}

interface SourcesDrawerProps {
  open: boolean
  apiKey: string
  onClose: () => void
  onReattach: (input: { sourceId: string; title: string }) => void
}

export function SourcesDrawer({ open, apiKey, onClose, onReattach }: SourcesDrawerProps) {
  const [items, setItems] = useState<RecentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    fetch('/api/cockpit/commentary/recent?limit=20', {
      headers: { 'X-API-Key': apiKey },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        const body = (await r.json()) as { items: RecentItem[] }
        setItems(body.items)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'failed'))
      .finally(() => setLoading(false))
  }, [open, apiKey])

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Recent sources</SheetTitle>
        </SheetHeader>
        {loading ? <div className="text-sm text-muted-foreground">Loading…</div> : null}
        {error ? <div className="text-sm text-destructive">Error: {error}</div> : null}
        <ul className="space-y-2 mt-4">
          {items.map((item) => (
            <li key={item.source_id} className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{item.source_name}</div>
                <div className="text-xs text-muted-foreground">
                  {item.source_type} • {new Date(item.approved_at).toLocaleDateString()}
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onReattach({ sourceId: item.source_id, title: item.source_name })}
                aria-label={`re-attach ${item.source_name}`}
              >
                Attach
              </Button>
            </li>
          ))}
        </ul>
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/sources-drawer.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/components/cockpit/chat/sources-drawer.tsx \
        cockpit-ui/components/cockpit/chat/sources-drawer.test.tsx
git commit -m "milestone(youtube-ingest): SourcesDrawer

Working: Opens, fetches /recent with X-API-Key, renders items, emits onReattach on click.
Tested: sources-drawer.test.tsx — 2 passed."
```

---

### Task 32: CitationLink deep-link component

**Files:**
- Create: `cockpit-ui/components/cockpit/chat/citation-link.tsx`
- Test: `cockpit-ui/components/cockpit/chat/citation-link.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// cockpit-ui/components/cockpit/chat/citation-link.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CitationLink } from './citation-link'

describe('CitationLink', () => {
  it('builds correct deep link with rounded timestamp', () => {
    render(
      <CitationLink videoId="abc123" segmentStartSeconds={125.4} />,
    )
    const link = screen.getByRole('link') as HTMLAnchorElement
    expect(link.href).toBe('https://youtu.be/abc123?t=125s')
    expect(link.textContent).toBe('▶ 2:05')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noreferrer noopener')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/citation-link.test.tsx`
Expected: FAIL — component missing.

- [ ] **Step 3: Write the implementation**

```tsx
// cockpit-ui/components/cockpit/chat/citation-link.tsx
interface CitationLinkProps {
  videoId: string
  segmentStartSeconds: number
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function CitationLink({ videoId, segmentStartSeconds }: CitationLinkProps) {
  const t = Math.max(0, Math.floor(segmentStartSeconds))
  const href = `https://youtu.be/${videoId}?t=${t}s`
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-xs underline-offset-2 hover:underline"
    >
      ▶ {formatTimestamp(segmentStartSeconds)}
    </a>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test components/cockpit/chat/citation-link.test.tsx`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/components/cockpit/chat/citation-link.tsx \
        cockpit-ui/components/cockpit/chat/citation-link.test.tsx
git commit -m "milestone(youtube-ingest): CitationLink

Working: Renders ▶ MM:SS linking to youtu.be/<id>?t=Ns, new tab, noreferrer.
Tested: citation-link.test.tsx — 1 passed."
```

---

### Task 33: WatchlistScreen + AddTickerDialog

**Files:**
- Create: `cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx`
- Create: `cockpit-ui/components/cockpit/watchlist/add-ticker-dialog.tsx`
- Test: `cockpit-ui/components/cockpit/watchlist/watchlist-screen.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// cockpit-ui/components/cockpit/watchlist/watchlist-screen.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { WatchlistScreen } from './watchlist-screen'

describe('WatchlistScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists items fetched from /api/cockpit/watchlist', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            { ticker: 'CBA.AX', added_at: '2026-04-18T00:00:00Z', source_id: 'yt_a', note: 'test', stance: 'watch' },
          ],
        }),
      }),
    )
    render(<WatchlistScreen apiKey="k" />)
    await waitFor(() => expect(screen.getByText('CBA.AX')).toBeInTheDocument())
  })

  it('surfaces 409 duplicate error inline', async () => {
    const fetchMock = vi
      .fn()
      // initial list
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      // POST returns 409
      .mockResolvedValueOnce({ ok: false, status: 409, text: async () => 'duplicate' })
    vi.stubGlobal('fetch', fetchMock)

    render(<WatchlistScreen apiKey="k" />)
    await userEvent.click(screen.getByRole('button', { name: /add ticker/i }))
    await userEvent.type(screen.getByLabelText(/ticker/i), 'BHP.AX')
    await userEvent.click(screen.getByRole('button', { name: /^add$/i }))
    await waitFor(() =>
      expect(screen.getByText(/already in watchlist/i)).toBeInTheDocument(),
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cockpit-ui && pnpm test components/cockpit/watchlist/`
Expected: FAIL — components missing.

- [ ] **Step 3: Write `add-ticker-dialog.tsx`**

```tsx
// cockpit-ui/components/cockpit/watchlist/add-ticker-dialog.tsx
'use client'

import { FormEvent, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface AddTickerDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (input: { ticker: string; note: string; stance: string }) => Promise<void>
  error: string | null
}

export function AddTickerDialog({ open, onClose, onSubmit, error }: AddTickerDialogProps) {
  const [ticker, setTicker] = useState('')
  const [note, setNote] = useState('')
  const [stance, setStance] = useState('watch')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await onSubmit({ ticker, note, stance })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add ticker</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label htmlFor="ticker">Ticker</Label>
            <Input
              id="ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="CBA.AX"
              required
            />
          </div>
          <div>
            <Label htmlFor="note">Note</Label>
            <Textarea id="note" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="stance">Stance</Label>
            <Input id="stance" value={stance} onChange={(e) => setStance(e.target.value)} />
          </div>
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              Add
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 4: Write `watchlist-screen.tsx`**

```tsx
// cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'

import { AddTickerDialog } from './add-ticker-dialog'

interface WatchlistItem {
  ticker: string
  added_at: string
  source_id: string | null
  note: string | null
  stance: string | null
}

interface WatchlistScreenProps {
  apiKey: string
}

export function WatchlistScreen({ apiKey }: WatchlistScreenProps) {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogError, setDialogError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const r = await fetch('/api/cockpit/watchlist', {
      headers: { 'X-API-Key': apiKey },
    })
    if (r.ok) {
      const body = (await r.json()) as { items: WatchlistItem[] }
      setItems(body.items)
    }
  }, [apiKey])

  useEffect(() => {
    load()
  }, [load])

  async function handleSubmit({ ticker, note, stance }: { ticker: string; note: string; stance: string }) {
    setDialogError(null)
    const r = await fetch('/api/cockpit/watchlist', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker, note, stance }),
    })
    if (r.status === 409) {
      setDialogError(`${ticker} is already in watchlist`)
      return
    }
    if (!r.ok) {
      setDialogError(`failed: ${r.status}`)
      return
    }
    setDialogOpen(false)
    await load()
  }

  async function handleRemove(ticker: string) {
    await fetch(`/api/cockpit/watchlist/${encodeURIComponent(ticker)}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': apiKey },
    })
    await load()
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Watchlist</h1>
        <Button onClick={() => setDialogOpen(true)}>Add ticker</Button>
      </div>
      <ul className="divide-y divide-border">
        {items.map((item) => (
          <li key={item.ticker} className="py-2 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium">{item.ticker}</div>
              {item.note ? <div className="text-xs text-muted-foreground">{item.note}</div> : null}
            </div>
            <Button variant="ghost" size="sm" onClick={() => handleRemove(item.ticker)}>
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <AddTickerDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false)
          setDialogError(null)
        }}
        onSubmit={handleSubmit}
        error={dialogError}
      />
    </div>
  )
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd cockpit-ui && pnpm test components/cockpit/watchlist/`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add cockpit-ui/components/cockpit/watchlist/
git commit -m "milestone(youtube-ingest): WatchlistScreen + AddTickerDialog

Working: Lists items, Add dialog with note/stance, surfaces 409 duplicate, supports Remove.
Tested: watchlist-screen.test.tsx — 2 passed."
```

---

### Task 34: Wire chat paste-to-ingest flow + sidebar entry

**Files:**
- Modify: `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- Modify: `cockpit-ui/components/cockpit/cockpit-shell.tsx` (or whichever file registers sidebar nav; confirm location before editing)

- [ ] **Step 1: Confirm sidebar registration location**

Run: `grep -rn "Watchlist\|sidebarItems\|navItems" cockpit-ui/components/cockpit/cockpit-shell.tsx cockpit-ui/components/cockpit/sidebar*`
Expected: find the nav items array the sidebar renders.

- [ ] **Step 2: Integrate IngestSummaryCard, TakeawaysPanel, SourcesDrawer into chat-screen**

Changes to `cockpit-ui/components/cockpit/chat/chat-screen.tsx`:

- Import: `useAttachedSources`, `extractYouTubeUrl`, `IngestSummaryCard`, `TakeawaysPanel`, `SourcesDrawer`.
- Add `const attached = useAttachedSources()` near the other hooks around line 197.
- Add state: `const [latestIngest, setLatestIngest] = useState<IngestSummary | null>(null)` and `const [takeaways, setTakeaways] = useState<TakeawaysPayload | null>(null)` and `const [sourcesOpen, setSourcesOpen] = useState(false)`.
- Extend `handleSend` (the function wired to `onSend` near line 1127) to intercept pasted YouTube URLs before dispatching to the normal chat pipeline:

```tsx
async function handleSend(userText: string): Promise<void> {
  const url = extractYouTubeUrl(userText)
  if (url) {
    const ingestResp = await fetch('/api/cockpit/commentary/ingest-url', {
      method: 'POST',
      headers: { 'X-API-Key': preferences.apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (!ingestResp.ok) {
      // surface error into chat log via existing error path; do not silently swallow.
      return
    }
    const body = await ingestResp.json()
    setLatestIngest({
      sourceId: body.source_id,
      title: body.title,
      chunkCount: body.chunk_count,
      detectedTickers: body.detected_tickers,
      status: body.status,
    })
    attached.attach({ sourceId: body.source_id, sourceKind: 'ephemeral', title: body.title })

    // fire takeaways in parallel
    const tkResp = await fetch('/api/cockpit/commentary/takeaways', {
      method: 'POST',
      headers: { 'X-API-Key': preferences.apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: body.source_id }),
    })
    if (tkResp.ok) {
      const tk = await tkResp.json()
      setTakeaways({
        sourceId: tk.source_id,
        videoId: String(body.source_id).replace(/^yt_/, ''),
        takeaways: tk.takeaways.map((t: any) => ({
          text: t.text,
          citations: t.citations.map((c: any) => ({
            chunkId: c.chunk_id,
            segmentStartSeconds: c.segment_start_seconds,
          })),
        })),
        watchlistSuggestions: tk.watchlist_suggestions.map((s: any) => ({
          ticker: s.ticker,
          commentary: s.commentary,
          citations: s.citations.map((c: any) => ({
            chunkId: c.chunk_id,
            segmentStartSeconds: c.segment_start_seconds,
          })),
        })),
        model: tk.model,
        promptVersion: tk.prompt_version,
      })
    }
    // build ephemeral index for this session so the next chat turn can retrieve
    await fetch('/api/cockpit/commentary/ephemeral-index', {
      method: 'POST',
      headers: { 'X-API-Key': preferences.apiKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, source_ids: [body.source_id] }),
    })
    return
  }

  // Normal chat path — forward attached sources.
  await sendChatTurn(userText, { attachedSources: attached.serialize() })
}
```

Implementer note: `sendChatTurn` is the existing send routine used by the current chat pipeline. Use whatever the current chat-screen calls (`sendMessage`, `handleSubmitMessage`, etc.). The only required change is threading `attached_sources: attached.serialize()` into its payload so the backend receives the new `ChatRequest.attached_sources` field.

Render `latestIngest`, `takeaways`, and `SourcesDrawer` within the chat view's side column or in-line above the composer — follow the existing layout for the news/commentary panes (they are the nearest analog).

Wire `onAddTicker` from IngestSummaryCard and TakeawaysPanel to POST `/api/cockpit/watchlist` with `{ticker, source_id, note, stance: 'watch'}` and surface 409 inline.

- [ ] **Step 3: Add sidebar entry for Watchlist**

Add a nav item whose `href` is `/watchlist` or whose tab id the existing shell uses. Mirror the style of neighboring nav items. Create the page file:

```tsx
// cockpit-ui/app/watchlist/page.tsx
'use client'

import { useEffect, useState } from 'react'

import { WatchlistScreen } from '@/components/cockpit/watchlist/watchlist-screen'

export default function WatchlistPage() {
  const [apiKey, setApiKey] = useState('')
  useEffect(() => {
    const k = localStorage.getItem('cockpit.apiKey') ?? ''
    setApiKey(k)
  }, [])
  if (!apiKey) return null
  return <WatchlistScreen apiKey={apiKey} />
}
```

If the cockpit-shell uses a tab-based router rather than Next App Router pages, instead register a `"watchlist"` tab that renders `<WatchlistScreen apiKey={…}/>` and adjust the sidebar accordingly. Confirm by reading the file referenced in Step 1 before editing.

- [ ] **Step 4: Manual smoke test**

Run backend + `pnpm dev`. In the chat, paste `https://youtu.be/dQw4w9WgXcQ`. Confirm:
- IngestSummaryCard appears with title + detected tickers
- Takeaways panel populates within ~15s
- Adding a ticker from the panel makes it appear in Watchlist page
- Next chat turn references the transcript content in its reply

- [ ] **Step 5: Commit**

```bash
git add cockpit-ui/components/cockpit/chat/chat-screen.tsx \
        cockpit-ui/components/cockpit/cockpit-shell.tsx \
        cockpit-ui/app/watchlist/
git commit -m "milestone(youtube-ingest): wire chat paste-to-ingest + watchlist sidebar entry

Working: Pasting a YouTube URL ingests, shows summary card, fetches takeaways, builds ephemeral index; next chat turn uses attachment; Watchlist sidebar entry renders list + Add dialog.
Tested: Manual smoke — paste → summary → takeaways → watchlist add → chat reply cites transcript."
```

---
