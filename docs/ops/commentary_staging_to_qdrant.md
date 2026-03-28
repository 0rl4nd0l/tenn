# Commentary staging → Qdrant (hot sources)

**Audience:** operators and developers running transcript/commentary ingest.  
**Contract:** Backend owns Qdrant writes and embeddings. Cockpit `/review` flows call the same promotion logic; do not index from a second, shadow pipeline.

## What “staging” means

1. Ingesting a **hot** source type (`youtube_transcript`, `podcast_transcript`, `market_commentary`) via `ingest_transcript` **does not** upsert vectors immediately.
2. Points are written under `~/.tenn/memory/staged_chunks/` as JSONL, and `index.json` records metadata (`source_id`, `collection_name`, `path`, `staged_at`, …).
3. Re-ingesting the same `source_id` skips re-staging and logs a warning (see `commentary_ingest.ingest_transcript`).

## Definition of done: “indexed”

- The staged JSONL for that `source_id` is **removed**.
- The entry is **removed** from `index.json`.
- Vectors exist in Qdrant in the recorded collection (default `commentary_chunks`, or `commentary_chunks_v2` if routing applied at ingest time).
- Source registry row (if present) has `review_status` **approved**.

## Prerequisites

- Qdrant reachable at the URL your backend uses (`QDRANT_URL` / normalized URL — see `app.core.config`).
- Embedding/collection dimension policy satisfied (same as normal commentary upsert).
- Backend dependencies available (use `financial-engine_v2/.venv`).

## Approve (promote to Qdrant)

### Option A — CLI (automation-friendly)

From repo root (or any cwd):

```bash
export PATH="/path/to/tenn/financial-engine_v2/.venv/bin:$PATH"
# Optional: match your backend env
# export QDRANT_URL=http://127.0.0.1:6333

python3 financial-engine_v2/scripts/promote_staged_commentary.py list
python3 financial-engine_v2/scripts/promote_staged_commentary.py approve --source-id 'youtube_transcript:example-channel:…'
```

### Option B — Cockpit TUI

Use the transcript review / `/review` commands (Stacks B in verification checklists) to approve pending items — implementation calls `TranscriptReviewService.approve` in `cockpit/integrations/transcript_review.py`.

## Reject (discard staging)

```bash
python3 financial-engine_v2/scripts/promote_staged_commentary.py reject --source-id 'youtube_transcript:…'
```

Removes staged file and index entry; sets registry `review_status` to **rejected** when registry is available.

## Rollback / safety

- **Before approve:** Inspect the JSONL file referenced in `index.json` (`path`). Each line is a Qdrant point payload + vector as produced at ingest time.
- **After a mistaken approve:** Removing points is a **separate** Qdrant operation (not automated here). Prefer reject **before** approve if unsure.
- **Stale staging:** `TranscriptReviewService.purge_expired(max_age_days=…)` exists for aged entries; wire to cron if needed.

## Related code

| Piece | Location |
|--------|-----------|
| Staging on ingest | `backend/app/services/commentary_ingest.py` |
| Approve / reject / list | `cockpit/integrations/transcript_review.py` |
| Qdrant upsert | `backend/app/services/embeddings.py` (`upsert_points`, `verify_qdrant`) |
| CLI wrapper | `financial-engine_v2/scripts/promote_staged_commentary.py` |

## What this runbook does *not* cover

- Changing embedding models or rebuilding collections (see vector baseline / SYSTEM_CONTRACT).
- Approving non-hot ingest paths (ASX PDF pipeline uses different storage and Qdrant collections).
