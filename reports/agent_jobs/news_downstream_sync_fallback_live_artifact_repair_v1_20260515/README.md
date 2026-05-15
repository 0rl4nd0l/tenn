# News Downstream Sync/Fallback Live Artifact Repair

## Verdict

repaired

The downstream repair completed for the approved 48-hour window. Qdrant `news_chunks` accepted 999 upserts with 0 deletes, and `news.sqlite` refreshed to newest `published_at=2026-05-14T16:21:46Z`.

## Session

- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD: `17ae93189290`
- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Lane: Query Orchestration
- Execution mode: SAFE EXTENSION / LIVE ARTIFACT MAINTENANCE
- Collision risk: MEDIUM
- Contested source surfaces touched: none

## Live Data Paths

- Articles DB: `/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite`
- Context DB: `/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news.sqlite`
- Nightly dir: `/mnt/hdd-data/home/l4nd0/tenn/reports/ops_checks/nightly`

## Backups

Backup dir:

`/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/backups/news_downstream_sync_fallback_live_artifact_repair_v1_20260515_20260515T061011Z`

Pre-sync and backup SHA256:

- `news_articles.sqlite`: `78ea73f6af618a8c7a901e571d727ff368049d2575d1ff62f8257d01b48712ee`
- `news.sqlite`: `6e8f70f0f38fce5805fc933d721f283a2ceb0bd5383535e8cc69464231c7556d`

Post-sync SHA256:

- `news_articles.sqlite`: `78ea73f6af618a8c7a901e571d727ff368049d2575d1ff62f8257d01b48712ee`
- `news.sqlite`: `8a7514fa6a671208a4f1de85f2c61f9834cd2839778b1e9b21c04d5f222966cd`

## Runtime Health

- Backend `:8000/api/health`: `{"status":"ok"}`
- llama.cpp `:8001/health`: `{"status":"ok"}`
- Cockpit `:8081/api/cockpit/health`: timed out after 5s; not used by the sync/fallback command.
- Ollama embed `:11434/api/embed`: succeeded for `nomic-embed-text`.
- Qdrant `/collections/news_chunks`: green, vector size 768.

## Before State

`news_articles.sqlite`:

- article count: 2510
- newest `published_at_utc`: `2026-05-14T16:21:46Z`
- newest `fetched_at_utc`: `2026-05-14T16:31:06Z`
- published articles May 13-15: May 13 = 145, May 14 = 93
- fetched articles May 13-15: May 13 = 151, May 14 = 153

`news.sqlite`:

- chunk count: 19506
- newest `published_at`: `2026-05-08T16:07:02Z`
- May 13-15 chunks: 0

Qdrant `news_chunks`:

- status: green
- points before: 19227
- May 13-15 payload count before: 0

## Command Run

Dry-run target report:

```bash
PYTHONPATH="/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend:/home/l4nd0/tenn-fast-dev-storage-v1/scripts${PYTHONPATH:+:${PYTHONPATH}}" \
  /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python3 \
  scripts/load_news_to_qdrant.py \
  --db-path /mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite \
  --qdrant-url http://127.0.0.1:6333 \
  --collection news_chunks \
  --since-hours 48 \
  --dry-run \
  --target-contract-report \
  --no-dispatch-memos
```

Dry-run target: 186 eligible articles, 999 chunks, 0 deletes.

First real run failed before Qdrant/fallback writes because settings resolved `ollama_url` to an empty string:

`Request URL is missing an 'http://' or 'https://' protocol.`

Successful repair command:

```bash
OLLAMA_URL="http://127.0.0.1:11434" \
PYTHONPATH="/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend:/home/l4nd0/tenn-fast-dev-storage-v1/scripts${PYTHONPATH:+:${PYTHONPATH}}" \
  /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python3 \
  scripts/load_news_to_qdrant.py \
  --db-path /mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite \
  --qdrant-url http://127.0.0.1:6333 \
  --collection news_chunks \
  --since-hours 48 \
  --refresh-sqlite-fallback \
  --news-context-db /mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news.sqlite \
  --memo-diagnostics-path /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/news_memos.jsonl \
  --memo-max-article-chars 5000 \
  --summary-json reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515/status.json \
  --no-dispatch-memos
```

The `--no-dispatch-memos` flag was added to keep this task scoped to downstream Qdrant/fallback repair and avoid queueing memo extraction work.

## After State

`news_articles.sqlite`:

- article count: 2510
- newest `published_at_utc`: `2026-05-14T16:21:46Z`
- newest `fetched_at_utc`: `2026-05-14T16:31:06Z`
- SHA256 unchanged.

`news.sqlite`:

- chunk count: 21538
- newest `published_at`: `2026-05-14T16:21:46Z`
- May 13-15 chunks: May 13 = 793, May 14 = 413
- May 10-12 chunks after rebuild: May 11 = 138, May 12 = 684
- verifier: `ok=true`, duplicate chunk IDs = 0

Qdrant `news_chunks`:

- status: green
- points after: 20226
- May 13-15 payload count after: 999
- May 10-12 payload count after: 0
- sync summary: `articles=186`, `chunks=999`, `upserted=999`, `deleted=0`

## SQLite Fallback Behavior

The existing loader only refreshes `news.sqlite` after successful Qdrant sync. The prior nightly summaries had `qdrant_sync.status=error` and `sqlite_fallback.status=not_run`; this run succeeded after setting `OLLAMA_URL`, so fallback refresh ran and returned `status=success`.

The fallback builder rebuilt the canonical context DB from the article DB with hash embeddings:

- articles seen: 2450
- articles chunked: 2449
- articles skipped: 1
- chunks written: 21495
- freshness status: fresh

## May 10-12 Status

May 10 remains DATA_MISSING in the queried local stores. May 11-12 are now present in `news.sqlite` because the fallback refresh rebuilt the context DB from `news_articles.sqlite`. Qdrant still has 0 points for May 10-12 because the approved sync command was bounded to the latest 48 hours and no broader backfill was run.

## Source Status

Active NVMe worktree after validation:

```text
?? docs/agent_tasks/news_downstream_sync_fallback_live_artifact_repair_v1_20260515.md
```

The generated report artifacts live under ignored `reports/` and must be added with `git add -f` if committed.

Preserve checkout status was already dirty before this task and remains dirty in tracked source files outside this job. No preserve source files were edited by this job.

The loader wrote ignored marker `financial-engine_v2/reports/news_chunks_embedding_model.txt` in the active worktree with value `nomic-embed-text`; it is ignored and not tracked. The preserve checkout already had the same marker value.

## Validation

- `python3 scripts/agent_job_contract.py validate ...`: ok
- `python3 scripts/agent_job_registry.py check-overlap ...`: ok
- registry claim: ok
- registry release: ok
- registry `list-active` after release: `active_jobs=[]`
- runtime health: backend ok, llama.cpp ok, Ollama embed ok, Qdrant ok, Cockpit health timed out
- Qdrant collection: green
- Qdrant points: 19227 before, 20226 after
- `python3 scripts/verify_news_context_db.py --db /mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news.sqlite`: ok
- `git diff --check`: ok

## Recommended Next Step

Add an explicit `--ollama-url` CLI option or loader fallback to `http://localhost:11434` when `settings.ollama_url` is empty, then schedule a separate approved Qdrant-only backfill for May 10-12 if those days must be semantically searchable.

## Project Memory Save Recommendation

Save that this live repair required `OLLAMA_URL=http://127.0.0.1:11434` when running `scripts/load_news_to_qdrant.py` from the NVMe worktree with the preserve venv, and that `--refresh-sqlite-fallback` rebuilds `news.sqlite` after Qdrant succeeds.
