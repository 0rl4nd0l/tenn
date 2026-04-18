# Cockpit Web UI: YouTube URL Ingest, Transcript Discussion, and Watchlist Suggestions

**Date:** 2026-04-18
**Status:** Draft
**Branch (origin):** `plan/ideation-combinations-2026-04-11`
**Predecessor:** `docs/superpowers/plans/2026-04-13-youtube-url-ingest.md` (TUI-side ingest, already shipped)

---

## Summary

Bring the YouTube URL paste-to-ingest feature, currently TUI-only, to the **cockpit-ui Next.js web UI** as the primary surface. Beyond paste-to-stage, this design adds:

1. **Drop-and-discuss** — pasting a YouTube link in chat stages the transcript and immediately attaches it to the current chat session as ephemeral context, so you can discuss it before approving.
2. **Lightweight summary card on stage** — 1-line summary, regex-detected ASX tickers, channel name, video metadata. No LLM cost.
3. **On-demand structured takeaways** — a "Generate takeaways" button runs an LLM pass producing key points + suggested watchlist tickers with verbatim quotes and timestamps. Cached per source.
4. **Watchlist as a first-class backend resource** — new SQLAlchemy table, REST API, and a top-level cockpit-ui tab. Suggested tickers from takeaways are **advisory only** — added one-click, never auto-added.
5. **Citation deep-links** — chunks preserve segment timestamps, so any chat citation from a YouTube source renders as a `▶ MM:SS` button that opens the video at that exact moment.
6. **Speaker / credibility surfacing** — channel name and a `credibility_weight`-derived badge appear next to citations.

The existing staging gate (`commentary_chunks` only receives chunks via explicit human approve) is preserved. Ephemeral attachment is what removes friction from the discuss-now path; approval is what makes a transcript globally retrievable across sessions.

---

## Motivation

Last session shipped `docs/superpowers/plans/2026-04-13-youtube-url-ingest.md` as a TUI-only feature. The user has confirmed the cockpit TUI is no longer used day-to-day; the cockpit-ui web app is the only client they interact with. Today the web UI:

- Forwards all slash commands generically to `/api/chat`, so a hypothetical `/ingest` would be answered as natural language rather than triggering ingestion.
- Has no YouTube URL paste detection.
- Has no review/approve UI for staged transcripts.
- Has no proxy route to `/api/commentary/*`.
- Has a `WatchlistItem` TypeScript interface but no actual watchlist screen and no backend HTTP API for watchlist data (TUI watchlist is a local SQLite table at `cockpit/storage/state.py` with no remote surface).

This spec closes that gap and uses the opportunity to make the watchlist a properly-modelled backend resource.

---

## Locked design decisions

| # | Decision | Choice |
|---|---|---|
| Q1 | Scope of integration | Full parity (paste, stage, attach to chat, discuss, review, approve, watchlist suggestions) |
| Q2 | Stage→approve gate UX | Hybrid: stage stays, but transcript is also attached as ephemeral context for immediate discussion |
| Q3 | When takeaways/suggestions appear | Lightweight summary card on stage + LLM analysis on-demand |
| Q4 | Watchlist persistence | New backend SQLAlchemy table + REST API |
| Q5 | Additional features in scope | Citation deep-links, watchlist notes carry quote+timestamp, recent-ingested tray, speaker/credibility surfacing. Per-video chat threads deferred. |
| Q6 | TUI parity needed | No — TUI never used; left untouched |
| Q7 | UI placement | Chat-screen right-edge drawer (3 tabs) + new top-level `Watchlist` sidebar tab |
| Q8 | LLM context for attached transcripts | Hybrid: short transcripts concat into prompt, long transcripts route through ephemeral session-scoped Qdrant collection. The concat-vs-ephemeral cutoff is an **implementation threshold** (currently ~4000 tokens) tunable in `tenn_chat.py`, NOT a stable API invariant — clients must not depend on the exact value. |
| Q9 | Watchlist DB | Both Postgres + SQLite via SQLAlchemy + Alembic, idempotent SQLite script (matches existing pattern) |
| Q10 | Watchlist suggestions | Suggest-only, one-click Add. **Advisory only — never auto-added.** |
| — | Architectural orchestration | Approach 2: web UI orchestrated, backend stays narrow |
| — | Market scope v1 | ASX-only ticker detection |
| — | Takeaways LLM path | Adaptive router (same as chat); persist `model` + `provider` + `prompt_version` on cached artifact |
| — | Takeaways cache invalidation | Manual "Regenerate" button; replaces cache; latest-only |
| — | Ephemeral retention | 7 days inactive, plus drop on explicit session deletion |
| — | Drawer tab labels | "In this chat" / "Pending review" / "Recent" |

---

## Invariants preserved

- **Single source of truth for retrieval.** `commentary_chunks` (production retrieval collection) only ever receives chunks via the existing human approve flow. Ephemeral session-scoped collections are isolated and never queried by normal retrieval paths.
- **Staging gate semantics unchanged.** `~/.tenn/memory/staged_chunks/` directory and the `transcripts/{id}/approve|reject` endpoints behave exactly as today.
- **Embed model + dimension lock.** Ephemeral collections use the same `EMBED_MODEL` and dimension as `commentary_chunks`. No new dimension config; startup validation unchanged.
- **`/chat` learning loop integrity.** Quality scorer, router optimizer, and chat preferences are not modified. Ephemeral chunks pass through `extra_context` and are merged before final ranking, but counted in a separate retrieval-precision bucket so they cannot pollute learned preferences.
- **Auth model unchanged.** All new endpoints use `require_api_key`. Cockpit-ui proxy routes forward `X-API-Key` per the existing `app/api/cockpit/action/execute/route.ts` pattern.
- **Watchlist additions are advisory only.** No code path auto-writes a row to `watchlist` from LLM output. Every row exists because of an explicit user action — manual add, suggestion-card click, or imported list. This matches the broader evidence-bound and confirmation-gated direction.
- **Non-canonical data boundary.** YouTube transcript chunks, generated takeaways, ticker suggestions, analyst quotes, and watchlist notes are **non-canonical contextual artifacts**. They MUST NEVER populate canonical financial-truth storage (`asx_periodic_financials`, `asx_risk_notes`, `extraction_runs`, or any future canonical metric table). They live exclusively in `commentary_chunks`, ephemeral collections, the takeaways cache, and the new `watchlist` table — all of which are explicitly contextual/curatorial, not authoritative.

---

## Architecture

### High-level data flow

```
┌────────────────────┐
│  cockpit-ui chat   │
│  (Next.js)         │
└──────────┬─────────┘
           │ paste YouTube URL
           v
┌────────────────────┐    ┌──────────────────────────┐
│ /api/cockpit/      │    │ /api/commentary/         │
│ commentary/        │───>│ ingest-url               │
│ ingest-url (proxy) │    │ (FastAPI)                │
└────────────────────┘    └──────────┬───────────────┘
                                     │ stage + summary + ticker scan
                                     v
                          ~/.tenn/memory/staged_chunks/<sid>.jsonl
                          + summary card returned to client
                                     │
                                     v
                          ┌──────────────────────────┐
                          │ cockpit-ui React state:  │
                          │ attachments[sessionId]   │ <── ephemeral, in-tab
                          │   = [{source_id, text,   │
                          │      video_meta, tickers}]│
                          └──────────┬───────────────┘
                                     │ next chat turn
                                     v
                          POST /api/chat {
                            session_id,
                            attached_sources: [sid, ...],
                            ...
                          }
                                     │
              ┌──────────────────────┴───────────────────────┐
              v                                              v
    short transcript (<=4k tok)                  long transcript (>4k tok)
    concat into prompt context                   POST /api/commentary/ephemeral-index
                                                 ↓
                                                 Qdrant collection:
                                                 commentary_ephemeral_<session_id>
                                                 ↓
                                                 retrieve top-K filtered by source_id
                                                                |
                                                                v
                          ┌──────────────────────────────────────────────┐
                          │ tenn_chat.py merges:                         │
                          │   - normal commentary_chunks retrieval       │
                          │   - news retrieval                           │
                          │   - ephemeral chunks (tagged source_kind)    │
                          │   - concat'd short transcripts (system block)│
                          └──────────────────────────┬───────────────────┘
                                                     v
                          LLM response with citations carrying video_id +
                          timestamp_seconds + source_kind
```

### Approach: web-UI orchestrated (selected)

The cockpit-ui owns "what is attached to this chat session" in client-side React state keyed by the existing `sessionId`. Backend remains mostly stateless except for the ephemeral Qdrant collection lifecycle (which is purely a retrieval optimisation, not session state).

Rejected alternatives:
- **Backend-orchestrated session store** — required new in-memory or Redis session store; too much architectural cost for this feature.
- **Hybrid TTL backend store** — same overhead, justified only if TUI parity matters; it doesn't.

---

## Backend additions

### New API endpoints

All under `/api`, all guarded by `require_api_key`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/commentary/ingest-url` | **Extend existing.** Response now includes `video_id`, `tickers_detected[]`, `summary_line`, `transcript_preview` (~500 chars), `transcript_token_estimate`. |
| GET | `/commentary/transcripts/{source_id}` | **New.** Return transcript JSONL (chunks + metadata + segment timings) so cockpit-ui can attach. Response shape: `{status: "pending" \| "approved", source_id, chunks, metadata, segment_timings}`. Resolution order: (1) if a staged JSONL exists at `~/.tenn/memory/staged_chunks/<source_id>.jsonl` → return with `status: "pending"`; (2) else if the source exists in the approved registry / `commentary_chunks` → reconstruct chunks from that store and return with `status: "approved"`; (3) else → `404 {"detail": "transcript not found"}`. The `status` field is the contract — clients use it to decide whether to surface Approve/Reject buttons (pending only) or only Detach (approved). |
| POST | `/commentary/takeaways/{source_id}` | **New.** Run LLM pass → `{summary, key_points[], suggested_tickers[{ticker, quote, timestamp_seconds, stance}]}`. Cached on disk; accepts `regenerate=true` query param to bypass cache. |
| POST | `/commentary/ephemeral-index` | **New.** `{session_id, source_id}`. Embeds chunks into `commentary_ephemeral_<session_id>`. Idempotent. Called only for long transcripts. |
| DELETE | `/commentary/ephemeral-index/{session_id}/{source_id}` | **New.** Remove one source's chunks from the session collection. Called on detach. |
| DELETE | `/commentary/ephemeral-index/{session_id}` | **New.** Drop the whole session collection. Called on session clear. |
| GET | `/commentary/recent` | **New.** Last 10 **approved YouTube/commentary sources** ordered by `approved_at desc`. Filtered to `kind in ("youtube", "commentary")` — does not include news, filings, or other source types. Returns `[{source_id, name, channel, video_id, approved_at}]`. Per-user filtering is out of scope for v1 (single-user system); the list is global, not "sources you touched". |
| GET | `/watchlist` | **New.** All watchlist rows. |
| POST | `/watchlist` | **New.** `{ticker, source_id?, note?, timestamp_seconds?}`. |
| DELETE | `/watchlist/{ticker}` | **New.** Remove by ticker. |
| GET | `/watchlist/{ticker}` | **New.** Single row. 404 if missing. |

### `/chat` extension

`ChatRequest` gains one optional field:

```python
attached_sources: list[str] | None = None  # source_ids attached to this session
```

Inside `tenn_chat.py`:
1. For each `source_id` in `attached_sources`, locate `~/.tenn/memory/staged_chunks/<source_id>.jsonl`. If missing, skip with a warning logged (do not fail the chat call).
2. Compute total estimated tokens across all attached transcripts.
3. If total is below the configured concat threshold (`CONCAT_TOKEN_THRESHOLD`, default `4000`, internal-only — not part of the public API) → concat raw transcript text into a system-message block tagged `attached_transcripts`.
4. Else → for each attached source, call into `commentary_ephemeral.query(session_id, source_id, query, top_k=8)` and include returned chunks.
5. Merge with existing `commentary_chunks` + news retrieval. Each chunk in the merged set carries `source_kind: "primary" | "ephemeral" | "news" | "concat"`.
6. Quality scorer treats `ephemeral` and `concat` chunks as a separate bucket — not mixed into `retrieval_precision` used by the learning loop.

### New SQLAlchemy model: `backend/app/models/watchlist.py`

```python
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    ticker: Mapped[str] = mapped_column(String(16), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- Alembic migration: `backend/app/alembic/versions/<rev>_add_watchlist.py` (Postgres).
- Idempotent SQLite script: `scripts/ensure_sqlite_watchlist_table.py` mirroring `ensure_sqlite_asx_created_at_columns.py`.
- Ticker is normalized to uppercase before insert; the API layer is responsible for normalization (matches TUI behaviour at `cockpit/storage/state.py:379`).

**Uniqueness model (v1):** `ticker` as PK enforces **one row per ticker**. A second add for the same ticker is a `409 Conflict` (the API does not silently overwrite existing `note` / `source_id` / `timestamp_seconds`). This is intentional for v1: the watchlist is a flat "what am I tracking" list, not an evidence log.

**Future path (out of scope for v1, noted to avoid lock-in):** when the watchlist needs to carry multiple supporting evidences per ticker (multiple analyst quotes from different videos, history of stance changes, dated rationales), the schema migrates to:
- `watchlist(ticker PK, added_at, current_stance)` — one row per ticker, summary state.
- `watchlist_evidence(id PK, ticker FK, source_id, note, timestamp_seconds, stance, recorded_at)` — many rows per ticker.

Designing the v1 API around `POST /watchlist {ticker, source_id?, note?, timestamp_seconds?}` makes that future split additive — `note` becomes the latest evidence excerpt while the full history moves to the child table — rather than a breaking change.

### New backend services

| Module | Role |
|---|---|
| `services/watchlist_service.py` | CRUD wrapper. Frozen dataclass DTOs. Functions: `list_all()`, `get(ticker)`, `add(WatchlistAddDTO)`, `remove(ticker)`. |
| `services/commentary_takeaways.py` | LLM pass producing structured takeaways via the adaptive router (same as `/chat`). Cache on disk at `~/.tenn/memory/takeaways/<source_id>.json` with fields: `source_id, generated_at, model, provider, prompt_version, summary, key_points, suggested_tickers`. |
| `services/commentary_ephemeral.py` | Session-scoped Qdrant collection lifecycle: `ensure_collection(session_id)`, `upsert(session_id, source_id, points)`, `query(session_id, source_id, query_vector, top_k)`, `drop_source(session_id, source_id)`, `drop_session(session_id)`. Reuses `embed_texts` and `EMBED_MODEL`. |
| `services/ticker_detector.py` | Regex `\b[A-Z]{3,4}\b` filtered against an ASX-ticker dictionary (sourced from existing source registry or a committed JSON file). v1 is ASX-only; structure leaves room for a `markets=["ASX","US"]` parameter later. |

### Extensions to existing services

| Module | Change |
|---|---|
| `services/youtube_transcript_fetcher.py` | Preserve `start_seconds` from each `youtube-transcript-api` segment through chunking. Each chunk gains `segment_start_seconds: float` and `segment_end_seconds: float` in payload. |
| `services/commentary_ingest.py` | Chunk payload gains `video_id: str | None` and `segment_start_seconds: float | None`. Backward compatible: existing staged JSONL files load with these fields as None. |
| `services/tenn_chat.py` | Implements the `/chat` extension above. Citations in the response include `video_id` and `timestamp_seconds` when available. |

### Ephemeral collection lifecycle

- **Naming:** `commentary_ephemeral_<session_id>` (the session UUID exactly as cockpit-ui generates it).
- **Created:** on first long-transcript attach within a session.
- **Dropped:**
  - Explicit `DELETE /api/commentary/ephemeral-index/{session_id}` from cockpit-ui (e.g., when user clears the session).
  - **Session-cleanup cron** (new `scripts/cleanup_ephemeral_collections.py`, scheduled daily): drops any `commentary_ephemeral_*` collection whose `session_id` has not appeared in the `/chat` access log for **7 days**.
  - On approve: chunks are migrated from ephemeral into `commentary_chunks` via the existing approve flow; the ephemeral copy of those chunks is then deleted (via `drop_source`).
- **Refresh handling:** browser refresh clears client-side attachment state, but the ephemeral collection is left for 7 days in case the user re-attaches the same source from the "Recent" tab.
- **Not queried** by `/chat` unless the request explicitly includes a matching `session_id` AND `attached_sources` containing source IDs whose chunks live there.

### Takeaways cache schema

`~/.tenn/memory/takeaways/<source_id>.json`:

```json
{
  "source_id": "yt_abc123",
  "generated_at": "2026-04-18T10:30:00Z",
  "model": "qwen3-30b-a3b-instruct",
  "provider": "llamacpp",
  "prompt_version": "takeaways_v1",
  "summary": "Bloomberg analyst Mary Smith outlines a bullish case for ASX-listed iron ore producers based on China stimulus expectations.",
  "key_points": [
    {"text": "China's Q1 stimulus likely to lift iron ore demand 5-8%", "timestamp_seconds": 142},
    ...
  ],
  "suggested_tickers": [
    {
      "ticker": "BHP",
      "quote": "BHP is my top pick — they're under-leveraged to iron ore right now",
      "timestamp_seconds": 412,
      "stance": "bullish"
    },
    ...
  ]
}
```

`stance` is one of `"bullish" | "bearish" | "neutral"` — enforced server-side via Pydantic enum.

Regenerate replaces this file in place (latest-only). The `prompt_version` field allows future prompt iterations to invalidate caches selectively.

### Session activity tracking for cleanup cron

The cleanup cron MUST NOT depend on parsing `/chat` access logs, web-server access logs, or any other indirectly-derived activity signal — those formats drift, rotate, and give the cron a stale or empty view of liveness. Locked design:

**Dedicated session-activity store:** `~/.tenn/memory/ephemeral_sessions.sqlite` (or a flat-file `ephemeral_sessions.json` if the SQLite import cost is excessive — implementation choice, but file-backed and dedicated to this purpose). Schema:

```
ephemeral_sessions(
  session_id TEXT PRIMARY KEY,
  last_activity_at TEXT NOT NULL,    -- ISO8601 UTC
  collection_name TEXT NOT NULL      -- "commentary_ephemeral_<session_id>"
)
```

**Write path (single writer):** `tenn_chat.py` UPSERTs `(session_id, now_utc)` on **every** `/chat` call that includes a `session_id`, regardless of whether the call uses ephemeral retrieval. This guarantees an active conversation keeps its ephemeral collection alive even if no attached transcripts are queried that turn. The write is best-effort and logged-on-failure — it must never block the chat response.

**Cron read path:** `scripts/cleanup_ephemeral_collections.py` reads the table, computes `now - last_activity_at > 7 days`, drops the matching Qdrant collection, and removes the row. Idempotent — safe to run multiple times per day. If the file is missing entirely (fresh install), the cron exits 0 silently.

**Insertion point:** `commentary_ephemeral.ensure_collection(session_id)` writes the row when a collection is first created (so the cron knows about every collection it might need to drop, not only those that have seen a chat turn).

This explicitly rules out the option-1/option-2 ambiguity from earlier drafts: there is one source of truth for "session_id last-seen", written by `tenn_chat.py` and `commentary_ephemeral`, read only by the cron.

---

## Frontend additions (cockpit-ui)

### New Next.js proxy routes

Mirror the `app/api/cockpit/action/execute/route.ts` pattern (forward headers including `X-API-Key`, stream JSON response, handle 502 on backend down):

| Path | Forwards to backend |
|---|---|
| `app/api/cockpit/commentary/ingest-url/route.ts` | `POST /api/commentary/ingest-url` |
| `app/api/cockpit/commentary/transcripts/[sourceId]/route.ts` | `GET /api/commentary/transcripts/{source_id}` |
| `app/api/cockpit/commentary/transcripts/[sourceId]/approve/route.ts` | `POST /api/commentary/transcripts/{source_id}/approve` |
| `app/api/cockpit/commentary/transcripts/[sourceId]/reject/route.ts` | `POST /api/commentary/transcripts/{source_id}/reject` |
| `app/api/cockpit/commentary/transcripts/pending/route.ts` | `GET /api/commentary/transcripts/pending` |
| `app/api/cockpit/commentary/takeaways/[sourceId]/route.ts` | `POST /api/commentary/takeaways/{source_id}` |
| `app/api/cockpit/commentary/ephemeral-index/route.ts` | `POST /api/commentary/ephemeral-index` |
| `app/api/cockpit/commentary/ephemeral-index/[sessionId]/[sourceId]/route.ts` | `DELETE` corresponding backend route |
| `app/api/cockpit/commentary/ephemeral-index/[sessionId]/route.ts` | `DELETE` corresponding backend route |
| `app/api/cockpit/commentary/recent/route.ts` | `GET /api/commentary/recent` |
| `app/api/cockpit/watchlist/route.ts` | `GET` and `POST /api/watchlist` |
| `app/api/cockpit/watchlist/[ticker]/route.ts` | `GET` and `DELETE /api/watchlist/{ticker}` |

### URL paste detection in chat

`components/cockpit/chat/chat-screen.tsx`: on message submit, run a YouTube URL regex over the message text. If matched:
1. Don't send to `/api/chat`.
2. Show optimistic chat bubble: "Ingesting <url>…".
3. Call `/api/cockpit/commentary/ingest-url` proxy.
4. On success: replace optimistic bubble with `IngestSummaryCard` (described below).
5. Add the new `source_id` to client-side `attachments[sessionId]` state.
6. If `transcript_token_estimate > 4000`: also fire `POST /commentary/ephemeral-index` to embed the long transcript into the session's Qdrant collection.
7. On failure: bubble shows error with retry button; nothing is added to attachments.

### New components

| Component | Purpose |
|---|---|
| `components/cockpit/chat/ingest-summary-card.tsx` | Card rendered inline in chat after a successful paste-ingest. Shows: video title, channel, duration, 1-line summary, ticker chips (clickable → adds to watchlist via Suggest-Only flow), "Generate takeaways" button, "Approve" button, "Reject" button, "Detach" button. |
| `components/cockpit/chat/takeaways-panel.tsx` | Expandable panel inside `IngestSummaryCard` showing structured takeaways once generated. Includes per-ticker suggestion cards with Add buttons. Has a "Regenerate" button. |
| `components/cockpit/chat/sources-drawer.tsx` | Right-edge drawer in chat-screen with three tabs: "In this chat" / "Pending review" / "Recent". Toggleable via a sidebar button. |
| `components/cockpit/chat/citation-link.tsx` | Renders a single citation in the chat answer. For YouTube sources: shows `▶ 12:34` button linking to `https://youtu.be/<video_id>?t=754s` in a new tab, plus channel name and credibility badge. For other sources: existing rendering. |
| `components/cockpit/watchlist/watchlist-screen.tsx` | New top-level screen for the `Watchlist` sidebar tab. Table view: ticker, added_at, source link (if present), note tooltip (analyst quote). Add and remove controls. |
| `components/cockpit/watchlist/add-ticker-dialog.tsx` | Manual add flow: ticker, optional note. |

### Sidebar updates

`components/cockpit/cockpit-sidebar.tsx`: add a new top-level item `Watchlist` (icon: list/bookmark). Position: between Operations and History.

### Client-side state shape

```typescript
// New: lib/cockpit-attachments.ts
interface AttachedTranscript {
  sourceId: string
  videoId: string
  videoUrl: string
  title: string
  channel: string
  durationSec: number | null
  publishedAt: string | null
  summaryLine: string
  tickersDetected: string[]
  tokenEstimate: number
  attachedAt: string  // ISO timestamp
}

interface SessionAttachments {
  [sessionId: string]: AttachedTranscript[]
}
```

Stored in React state (or a small Zustand/atom store if cockpit-ui already uses one — to be confirmed during implementation). NOT persisted to localStorage — refresh = drop, matching the locked UX decision.

### Watchlist screen

- Lists rows from `GET /api/watchlist`.
- Each row: ticker, added_at, "from <video title>" link if `source_id` present (clicking opens the video URL with timestamp), tooltip showing the analyst quote (`note` field), remove button.
- Top of screen: manual add dialog.
- Empty state: explainer pointing to the chat ingest flow.

---

## End-to-end flow

### Flow A: paste a short video and discuss

1. User pastes `https://youtu.be/abc123` into chat.
2. Chat-screen detects URL, suppresses sending to `/chat`, calls `POST /api/cockpit/commentary/ingest-url`.
3. Backend: `fetch_video_metadata` → `fetch_transcript` → `ingest_transcript` (stages chunks). Returns summary card data: `source_id, video_id, title, channel, summary_line, tickers_detected: ["BHP","RIO"], transcript_token_estimate: 3200`.
4. Cockpit-ui renders `IngestSummaryCard` in chat. Adds the source to `attachments[sessionId]`.
5. Token estimate is ≤ 4000 → no ephemeral index call.
6. User types: "What's the analyst's main thesis on iron ore?"
7. Cockpit-ui sends `POST /api/chat {session_id, message, attached_sources: [source_id]}`.
8. Backend `tenn_chat.py`: loads staged JSONL, concats raw text into `attached_transcripts` system block, merges with normal retrieval, calls LLM. Response includes citations with `video_id` + `timestamp_seconds`.
9. Citations render as `▶ 8:42` deep-link buttons.
10. User clicks "Generate takeaways" on the summary card.
11. Cockpit-ui calls `POST /api/cockpit/commentary/takeaways/<source_id>`.
12. Backend runs LLM pass via adaptive router; caches result; returns structured takeaways.
13. `TakeawaysPanel` renders key points + ticker suggestion cards.
14. User clicks "Add to watchlist" on the BHP card. Cockpit-ui calls `POST /api/cockpit/watchlist {ticker:"BHP", source_id, note: <quote>, timestamp_seconds: 412}`.
15. Toast confirms; suggestion card flips to "Added" state.

### Flow B: paste a long video

Identical to Flow A through step 4, except:
5'. Token estimate > 4000 → cockpit-ui fires `POST /api/cockpit/commentary/ephemeral-index {session_id, source_id}` in the background.
6'. Backend embeds chunks into `commentary_ephemeral_<session_id>` (creates collection if missing), returns `{ok: true, chunks_indexed: N}`.
7'. User chat turn now triggers backend retrieval against the ephemeral collection (top-K filtered by `source_id`) instead of full concat.

### Flow C: approve a transcript for persistent storage

1. User clicks "Approve" on the IngestSummaryCard (or in the "Pending review" drawer tab).
2. Cockpit-ui calls `POST /api/cockpit/commentary/transcripts/<source_id>/approve`.
3. Backend: existing `approve_transcript` flow upserts chunks into `commentary_chunks`; deletes from staging; updates source registry.
4. Cockpit-ui then calls `DELETE /api/cockpit/commentary/ephemeral-index/<session_id>/<source_id>` to remove the now-redundant ephemeral copy (only if it existed; long videos only).
5. Source moves from "In this chat" → "Recent" in the drawer.
6. From now on, this source is retrievable across all sessions via the normal commentary retrieval path.

### Flow D: reject a transcript

1. User clicks "Reject" on the IngestSummaryCard or in "Pending review".
2. Cockpit-ui calls `POST /api/cockpit/commentary/transcripts/<source_id>/reject`.
3. Backend: existing `reject_transcript` purges staged file and updates registry.
4. Cockpit-ui calls `DELETE /api/cockpit/commentary/ephemeral-index/<session_id>/<source_id>` if applicable.
5. Source removed from `attachments[sessionId]`.
6. Toast: "Transcript rejected and purged."

### Flow E: detach without rejecting

1. User clicks "Detach" on the IngestSummaryCard.
2. Source removed from `attachments[sessionId]` (client-side only).
3. If long video: `DELETE /api/cockpit/commentary/ephemeral-index/<session_id>/<source_id>` to free Qdrant resources.
4. The staged transcript is left intact in `~/.tenn/memory/staged_chunks/` so it still appears in "Pending review" and can be re-attached or approved later.

### Flow F: re-attach from "Recent" tab

1. User opens the drawer's "Recent" tab and clicks a previously-approved source.
2. Cockpit-ui calls `GET /api/cockpit/commentary/transcripts/<source_id>` to retrieve the transcript text + metadata.
3. Source added to `attachments[sessionId]`. If long: ephemeral index call. From the chat's perspective, behaves identically to a fresh attachment — except this source is *also* retrievable from the global `commentary_chunks` collection.

---

## Citation deep-links

When `tenn_chat.py` returns chunks for the response, each chunk's payload may now include `video_id` and `segment_start_seconds`. The chat response shape gains:

```json
{
  "answer": "...",
  "citations": [
    {
      "chunk_id": "...",
      "source_id": "yt_abc123",
      "source_kind": "ephemeral",
      "speaker": "Bloomberg Markets",
      "credibility_weight": 0.85,
      "video_id": "abc123",
      "timestamp_seconds": 754,
      "snippet": "BHP is my top pick — they're under-leveraged..."
    }
  ]
}
```

`citation-link.tsx` renders each citation as:

```
[▶ 12:34] Bloomberg Markets · ●●● (high credibility)
"BHP is my top pick — they're under-leveraged..."
```

The `▶ 12:34` button opens `https://youtu.be/abc123?t=754s` in a new tab. The credibility badge maps `credibility_weight`:

- `>= 0.7` → "high" (green)
- `0.3 <= w < 0.7` → "medium" (amber)
- `< 0.3` → "low" (grey)

---

## Error handling and edge cases

| Case | Behaviour |
|---|---|
| YouTube URL with no transcript (private, no captions, age-restricted) | Backend returns 422 with `transcript unavailable: <reason>`. Cockpit-ui shows error in the optimistic chat bubble: "Couldn't ingest: no transcript available." Nothing added to attachments. |
| URL is not YouTube | Backend regex rejects with 422. Cockpit-ui shows "Only YouTube URLs supported in v1." |
| Backend is down | Proxy route returns 502 with `backend: <url>`. Chat bubble shows "Backend unreachable" with retry button. |
| Network drop mid-ingest | Proxy route times out (15-min limit, same as `action/execute`). Chat bubble shows timeout error. |
| Same URL ingested twice | Backend `ingest_transcript` already idempotent on `source_id`. Returns existing source_id; cockpit-ui treats as success and attaches normally. |
| Approve while ephemeral collection has not finished indexing | Approve flow does not depend on ephemeral collection. The cleanup `DELETE` after approve succeeds even if there's nothing to delete (idempotent). |
| User refreshes browser mid-chat | Attachments dropped (matches locked UX). Ephemeral collection persists for 7 days; user can re-attach from "Recent" or "Pending review" tab. |
| Session cleanup cron drops collection while user actively chatting | Cron only drops collections inactive ≥ 7 days, so this should not happen. As a safety net: if `tenn_chat.py` queries an ephemeral collection that doesn't exist, it logs a warning and falls back to skipping ephemeral retrieval (still answers the question with whatever else it has). |
| LLM takeaway pass times out | Backend returns 504. Cockpit-ui keeps the "Generate takeaways" button enabled; no cache write. |
| Suggested ticker that's already in watchlist | `POST /watchlist` returns 409. Cockpit-ui shows "Already in watchlist" toast; suggestion card flips to "Added" state anyway. |
| Watchlist add for unknown ticker (not in ASX dictionary) | Allowed in v1 — the watchlist accepts any string up to 16 chars, uppercased. Future enhancement could validate against a registry. |
| Two tabs from same session | `attachments` is per-tab React state — they won't share. Each tab independently attaches and detaches. The ephemeral Qdrant collection is keyed by session_id, so both tabs' attached sources land in the same collection. This is acceptable: queries filter by `source_id`. |
| Approve while another session has same source attached | Approve succeeds. Other session's ephemeral copy is left intact (the cleanup `DELETE` is keyed by the approving session's ID). The other session continues to work; the source is also now in `commentary_chunks` so retrieval may double-count. Acceptable for v1; documented for future cleanup. |

---

## Testing approach

### Backend (pytest)

| Test file | What it covers |
|---|---|
| `backend/tests/test_commentary_endpoints.py` | **Extend** existing. New cases: `ingest-url` extended response shape (tickers, summary, token estimate); `transcripts/{id}` GET returns staged JSONL; `takeaways/{id}` POST returns structured + caches + regenerate=true bypasses cache. |
| `backend/tests/test_commentary_ephemeral.py` | **New.** Lifecycle: `ensure_collection` idempotent; `upsert` then `query` returns chunks; `drop_source` removes only that source's chunks; `drop_session` drops collection; query against missing collection returns empty list (not error). |
| `backend/tests/test_watchlist_endpoints.py` | **New.** GET/POST/DELETE; ticker normalization (lowercase input → uppercase stored); 404 on missing; 409 on duplicate; non-empty `note` and `timestamp_seconds` round-trip correctly. |
| `backend/tests/test_chat_with_attached_sources.py` | **New.** `/chat` with `attached_sources` containing a small source: concat path triggers, transcript text appears in prompt context, response cites it. With a large source: ephemeral query path triggers, citations carry `source_kind: "ephemeral"`. With invalid source_id: warning logged, chat still succeeds. |
| `backend/tests/test_ticker_detector.py` | **New.** Regex matches obvious cases (BHP, RIO, FMG); filters non-tickers (THE, CEO, AND); handles transcripts with no tickers; ASX dictionary loaded from registry. |
| `backend/tests/test_youtube_transcript_chunking.py` | **Extend.** Chunks now carry `segment_start_seconds`; backward-compat: chunks without it still load. |
| `scripts/test_cleanup_ephemeral_collections.py` | **New.** Cron logic: collection with no `/chat` activity in 7 days is dropped; active collection is preserved; missing log file does not crash. |

### Frontend (Vitest / React Testing Library)

| Test file | What it covers |
|---|---|
| `cockpit-ui/components/cockpit/chat/__tests__/chat-screen-ingest.test.tsx` | **New.** Pasting a YouTube URL triggers ingest proxy call; renders `IngestSummaryCard` on success; shows error on 422; updates `attachments` state. |
| `cockpit-ui/components/cockpit/chat/__tests__/ingest-summary-card.test.tsx` | **New.** Renders ticker chips; "Generate takeaways" calls proxy; "Approve" / "Reject" / "Detach" trigger correct calls and state updates. |
| `cockpit-ui/components/cockpit/chat/__tests__/takeaways-panel.test.tsx` | **New.** Renders key points and suggestion cards; "Add to watchlist" calls proxy with note + timestamp; "Regenerate" bypasses cache. |
| `cockpit-ui/components/cockpit/chat/__tests__/citation-link.test.tsx` | **New.** YouTube citation renders timestamp button with correct `?t=Ns` URL; non-YouTube falls back to existing rendering; credibility badge maps weight correctly. |
| `cockpit-ui/components/cockpit/watchlist/__tests__/watchlist-screen.test.tsx` | **New.** Renders watchlist rows; manual add dialog calls proxy; remove button works; empty state shown when list empty. |

### E2E (Playwright)

| Journey | Steps |
|---|---|
| `e2e/cockpit/youtube-ingest-and-discuss.spec.ts` | Open chat → paste short YouTube URL → wait for IngestSummaryCard → ask follow-up question → assert response cites the video → click "Generate takeaways" → click "Add" on a suggestion → switch to Watchlist tab → assert ticker present. |
| `e2e/cockpit/youtube-approve-flow.spec.ts` | Paste URL → click Approve → switch to drawer "Recent" tab → assert source listed. Detach handling: paste URL → click Detach → assert source removed from "In this chat" but present in "Pending review". |

### Coverage targets

- Backend new modules: 80%+ line coverage per project rules.
- Cockpit-ui new components: 80%+ line coverage.
- E2E: at least the two journeys above must pass against a fully-running local stack.

---

## Out of scope (deferred to future)

- Per-video focused chat threads (Q5).
- TUI parity for ephemeral attach / drop-and-discuss (TUI keeps existing stage→approve→retrieve flow).
- TUI watchlist migration to consume backend API (TUI watchlist becomes legacy/dead code; not removed in this scope).
- Auto-add (Q10A) or confidence-tiered auto-add (Q10C).
- Non-YouTube ingest sources (Spotify, Apple Podcasts, RSS, plain articles).
- Transcript language / translation.
- Sector auto-tagging from transcript content.
- Multi-video synthesis presets ("compare what these videos say about X").
- Credibility-weight tuning UI.
- Watchlist-driven alerts ("notify me when ticker X appears in any future ingest").
- Cross-ticker dashboards.
- Cached structured summaries as a speed optimization over on-demand takeaways.
- Approach 3 migration (backend TTL ephemeral store) — requires TUI to become an active surface again.
- Cleanup of duplicate chunks when a source is approved while another session still has it ephemeral.

---

## Risks and mitigations

**Collision risk: MEDIUM.** This change is not isolated. It touches several shared surfaces simultaneously: `tenn_chat.py` (chat orchestration — also currently modified by the visible-source-grounding milestone), `commentary_ingest` and `commentary_takeaways` paths (extraction-truth area), Qdrant collection lifecycle (shared with `commentary_chunks` and news indexes), and cockpit-ui chat state (also currently modified by verification screen and offline-indicator work on this branch). Concurrent in-flight work on any of these surfaces increases the chance of merge conflicts and silent regressions. Mitigation: phase the implementation so backend foundation (Phase 1) lands as one commit, the `/chat` extension (Phase 2) lands as a second commit gated on a green retrieval-baseline run, and the cockpit-ui changes (Phases 3–4) land last so chat-screen edits rebase onto already-merged backend changes rather than the other way around.

| Risk | Mitigation |
|---|---|
| Ephemeral Qdrant collections accumulate without bound | Daily cleanup cron with 7-day inactivity threshold + explicit drop on session delete. |
| Merge conflicts on `tenn_chat.py` and `chat-screen.tsx` (both under active edit on this branch) | Phase 2 (chat extension) lands only after current visible-source-grounding work is committed; Phase 4 (cockpit-ui) rebases on Phases 1–3. Each phase is a self-contained milestone commit per the project commit protocol. |
| Silent regression in retrieval quality from `attached_sources` merge logic | Quality scorer separation by `source_kind` ensures ephemeral chunks cannot move learned-preferences metrics. Phase 2 includes a baseline-comparison step on the existing retrieval-precision suite before merge. |
| Long video token estimate is wrong → concat path used for too-long transcript | Fall back: if concat would exceed model context, backend logs and switches to ephemeral path on the fly. Estimate uses `len(text) // 4` as a fast approximation; refine later if needed. |
| Cockpit-ui state loss on refresh frustrates user | "Recent" drawer tab makes re-attach a single click. The stage is preserved in `~/.tenn/memory/staged_chunks/` so nothing is actually lost. |
| Watchlist becomes dual source of truth (backend + TUI SQLite) | Documented as legacy; TUI is unused per Q6. Future cleanup task scheduled in Future Upgrades. |
| Suggested tickers include false positives ("CEO", "THE") | ASX dictionary filter should catch these. Tests include adversarial cases. |
| `/chat` learning loop polluted by ephemeral retrieval scores | `source_kind` tag separates ephemeral from primary; quality scorer only counts primary chunks toward `retrieval_precision`. |
| User pastes URL but transcript pass-through fails silently | Tests include: missing transcript, 422 path, network drop, retries. Optimistic chat bubble is replaced with explicit error state — never silent. |

---

## Dependencies and prerequisites

**Backend:**
- Existing: `fastapi`, `pydantic`, `sqlalchemy`, `alembic`, `qdrant-client`, `youtube-transcript-api`, `yt-dlp`.
- No new dependencies required.

**Frontend:**
- Existing: `next`, `react`, `swr`/`react-query` (whichever cockpit-ui already uses).
- No new dependencies required.

**Configuration:**
- No new env vars required.
- New cron: add `scripts/cleanup_ephemeral_collections.py` to `docs/ops/` runbook for periodic execution (cron, systemd timer, or `make` target — TBD with ops).

---

## Implementation phasing

The writing-plans skill will decompose this spec into subagent-driven tasks. Suggested phasing for that decomposition:

**Phase 1 — Backend foundation (parallelisable subagent tasks)**
- Watchlist model + migration + SQLite script + service + endpoints.
- `commentary_ephemeral` service + lifecycle endpoints + cleanup cron.
- `ticker_detector` service.
- Extend `youtube_transcript_fetcher` and `commentary_ingest` for segment timestamps + video_id.
- Extend `ingest-url` response.
- New `transcripts/{id}` GET endpoint.
- New `takeaways/{id}` endpoint + cache.
- New `recent` endpoint.

**Phase 2 — Backend chat extension (depends on Phase 1)**
- Extend `tenn_chat.py` `/chat` to accept `attached_sources` and route between concat and ephemeral retrieval.
- Citations carry `video_id` + `timestamp_seconds`.
- Quality scorer separation of `source_kind`.

**Phase 3 — Cockpit-ui proxy routes (parallelisable, can start with Phase 1)**
- All new `app/api/cockpit/commentary/*` and `app/api/cockpit/watchlist/*` routes.

**Phase 4 — Cockpit-ui components (depends on Phase 3)**
- `IngestSummaryCard`, `TakeawaysPanel`, `SourcesDrawer`, `CitationLink`, `WatchlistScreen`, `AddTickerDialog`.
- URL paste detection in `chat-screen.tsx`.
- Sidebar update.
- Client-side attachments state.

**Phase 5 — Tests + E2E + ops integration**
- Backend pytest, frontend Vitest, Playwright journeys.
- Add cleanup cron to ops docs.
- Update `docs/claude/STATE.md` and any relevant CLAUDE.md files.

---

## Acceptance criteria

A user, opening only the cockpit-ui web app:

1. Can paste a YouTube URL into chat and within ~10s see an `IngestSummaryCard` with title, channel, summary, and ticker chips.
2. Can immediately ask the LLM about the video's content and receive an answer that cites specific moments (timestamp deep-links work and open the video at the right second).
3. Can click "Generate takeaways" and receive a structured analysis with key points and per-ticker suggestion cards including verbatim quotes.
4. Can click "Add to watchlist" on a suggestion and see it appear in the new Watchlist tab with the analyst quote attached.
5. Can approve the transcript for permanent retrieval, and discover the source in the "Recent" drawer tab afterwards.
6. Can reject a bad transcript and have it purged from staging.
7. Can refresh the browser and not lose anything important: approved transcripts still queryable; the watchlist intact; pending reviews still in the "Pending review" tab; only the "what's attached to this chat" state is reset (and the "Recent" tab makes re-attach one click).
8. Never sees a watchlist row that wasn't created by an explicit human action.
