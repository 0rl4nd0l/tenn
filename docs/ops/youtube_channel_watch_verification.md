# YouTube channel watch verification

**Audience:** Tenn/Cockpit operators verifying natural-language YouTube channel watch commands.

**Contract:** Cockpit may request channel registration, but backend owns the channel registry, transcript ingestion, staging, Qdrant promotion, and retrieval. Do not write channel registry files or Qdrant points from Cockpit-side code.

## What the command proves

The chat command:

```text
watch youtube kneppy invests
```

proves only the first step when it succeeds: the backend resolved a YouTube channel and wrote it to the backend-owned channel registry.

It does **not** by itself prove that:

- a background channel poller is running,
- any videos have usable transcripts,
- transcript chunks have been approved into Qdrant,
- chat answers are retrieving those chunks.

Those are separate checkpoints.

## Current live checkpoint

Observed after the 2026-04-29 fixes:

- `/api/commentary/channels` contained `Kneppy Invests`, `channel_id=UCjQJPzeCJhA4KrETh3FVVHA`, `enabled=true`.
- `/api/commentary/transcripts/pending` returned `count=0`.
- No `run_transcript_daemon.py` / `YoutubeTranscriptFetcher` process was visible in `ps`.
- `financial-engine_v2/scripts/run_transcript_daemon.py` currently wires `TranscriptWatcher`, which scans dropped transcript files, not `YoutubeTranscriptFetcher`, which polls registered YouTube channels.

Interpretation: channel registration is working; automatic scheduled channel polling is not proven by the current process/code evidence.

## Verification ladder

Run these checks in order. Stop at the first failing layer.

### 1. Verify the backend is alive

```bash
curl -sS http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok"}
```

### 2. Verify the channel is registered

```bash
curl -sS http://127.0.0.1:8000/api/commentary/channels | python3 -m json.tool
```

Expected shape:

```json
{
  "channels": [
    {
      "name": "Kneppy Invests",
      "channel_id": "UCjQJPzeCJhA4KrETh3FVVHA",
      "credibility_weight": 0.55,
      "enabled": true
    }
  ],
  "count": 1
}
```

If this is empty, run the chat command again or call the backend directly:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/commentary/channels \
  -H "Content-Type: application/json" \
  -d '{"name_or_id":"Kneppy Invests"}' \
  | python3 -m json.tool
```

### 3. Check whether scheduled polling is running

```bash
ps -eo pid,ppid,cmd \
  | rg -i 'run_transcript_daemon|YoutubeTranscriptFetcher|youtube_transcript|transcript' \
  | rg -v 'rg -i'
```

If no relevant process appears, scheduled channel polling is not proven. Registration alone will not fetch new videos unless a poller is running or a one-shot poll is executed.

### 4. Force one channel poll

This is state-changing: it fetches recent videos for enabled channels, fetches transcripts when available, and stages transcript chunks for review.

```bash
docker exec fe_backend python - <<'PY'
from app.services.youtube_transcript_fetcher import YoutubeTranscriptFetcher

for result in YoutubeTranscriptFetcher(video_limit=2).poll_once():
    print(result)
PY
```

Expected outcomes:

- one or more `TranscriptProcessResult(...)` rows means transcript files were processed;
- no output means no new transcript was staged, usually because videos were duplicates, unavailable, or transcript fetch failed/was skipped.

### 5. Verify transcripts are staged for review

```bash
curl -sS http://127.0.0.1:8000/api/commentary/transcripts/pending | python3 -m json.tool
```

Expected after a successful new poll:

```json
{
  "pending": [
    {
      "source_id": "youtube_transcript:...",
      "source_type": "youtube_transcript",
      "source_name": "...",
      "chunk_count": 12,
      "collection_name": "commentary_chunks"
    }
  ],
  "count": 1
}
```

Important: hot sources are staged, not automatically indexed. This is deliberate. See [commentary_staging_to_qdrant.md](commentary_staging_to_qdrant.md).

### 6. Approve a staged transcript into Qdrant

```bash
SOURCE_ID="paste_source_id_here"

curl -sS -X POST \
  "http://127.0.0.1:8000/api/commentary/transcripts/${SOURCE_ID}/approve" \
  | python3 -m json.tool
```

Expected:

```json
{
  "ok": true,
  "source_id": "youtube_transcript:...",
  "chunks_indexed": 12,
  "collection": "commentary_chunks"
}
```

After approval, the item should disappear from pending review.

### 7. Verify Qdrant contains the approved channel chunks

```bash
docker exec fe_backend python - <<'PY'
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from app.core.config import settings

client = QdrantClient(url=settings.qdrant_url)
flt = Filter(must=[
    FieldCondition(key="speaker", match=MatchValue(value="Kneppy Invests"))
])

for collection in ("commentary_chunks", "commentary_chunks_v2"):
    try:
        count = client.count(
            collection_name=collection,
            count_filter=flt,
            exact=True,
        ).count
        print(f"{collection}: {count}")
    except Exception as exc:
        print(f"{collection}: unavailable ({exc})")
PY
```

Expected: at least one commentary collection shows a count greater than zero.

### 8. Verify chat can use commentary

Use `/chat`, not `/rag/query`. The current `/rag/query` route returns `501` for `source="commentary"` and tells callers to use `/chat`.

```bash
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mode":"analysis","message":"Using commentary sources, what has Kneppy Invests said recently?"}' \
  | python3 -m json.tool
```

Evidence of use:

- response sources include `source_type: youtube_transcript`, or
- source/chunk payloads mention `speaker: Kneppy Invests`, or
- logs show `tenn_chat` retrieving from `commentary_chunks`.

If the answer says there is not enough retrieved context, the channel may be registered but not yet approved into Qdrant, or retrieval did not match the query.

## Known gap

The current daemon entrypoint:

```bash
financial-engine_v2/scripts/run_transcript_daemon.py
```

constructs and runs `TranscriptWatcher`, which watches `inbox/transcripts/*.txt`. It does not currently construct `YoutubeTranscriptFetcher` or call `maybe_poll()` for registered channels.

The proper remediation is to extend this daemon so each loop:

1. runs `TranscriptWatcher.poll_once()` for manually dropped transcript files;
2. runs `YoutubeTranscriptFetcher.maybe_poll()` for enabled registry channels;
3. prints separate summaries for watcher and channel poller results;
4. preserves the human review gate before Qdrant promotion.

Do not bypass the review gate by auto-upserting fetched YouTube transcripts.

## Troubleshooting

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Channel command succeeds, but no pending transcripts | Poller is not running, no new videos, duplicate source, or transcripts unavailable | Steps 3-5 |
| Pending transcripts exist, but chat cannot use them | They are staged only, not approved into Qdrant | Steps 5-7 |
| Qdrant has chunks, but chat does not cite them | Query did not retrieve matching commentary chunks | Step 8 with a query naming the speaker |
| `/rag/query` with `source="commentary"` returns 501 | Commentary retrieval is currently via `/chat` | Use Step 8 |
| Plain channel name resolves wrong channel | YouTube search ambiguity | Register with exact channel URL or `UC...` id |

## Related code

| Layer | File |
| --- | --- |
| Channel registry | `financial-engine_v2/backend/app/services/channel_registry.py` |
| Channel registration API | `financial-engine_v2/backend/app/api/commentary.py` |
| Channel polling/fetching | `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py` |
| Transcript staging | `financial-engine_v2/backend/app/services/commentary_ingest.py` |
| File-drop watcher daemon | `financial-engine_v2/scripts/run_transcript_daemon.py` |
| Qdrant approval API | `financial-engine_v2/backend/app/api/commentary.py` |
| Chat commentary retrieval | `financial-engine_v2/backend/app/services/tenn_chat.py` |
