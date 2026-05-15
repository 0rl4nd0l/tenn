---
job_id: news_downstream_sync_fallback_live_artifact_repair_v1_20260515
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_NEWS_SYNC_FALLBACK_LIVE_ARTIFACT_REPAIR_20260515_GPT
production_data_access: false
live_data_maintenance: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515
allowed_files:
  - docs/agent_tasks/news_downstream_sync_fallback_live_artifact_repair_v1_20260515.md
  - reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515/README.md
  - reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515/status.json
  - reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515/diff-check.json
---

# Task

Repair or verify the downstream news sync/fallback using the canonical ignored news artifact paths from the preserve checkout. Do not refetch all news, wipe Qdrant, or edit source code.

Primary lane: Query Orchestration
Supporting lanes: Provenance / Reporting / Evaluation
Mode: SAFE EXTENSION / LIVE ARTIFACT MAINTENANCE
Expected collision risk: MEDIUM

# Context

Previous news repair attempts were safe but did not run the actual sync:

1. First retry blocked because another Query Orchestration job held the registry lane.
2. Second retry claimed successfully, but the isolated worktree lacked ignored data paths:
   - `reports/ops_checks/nightly`
   - `reports/qual_context/news_articles.sqlite`
   - `reports/qual_context/news.sqlite`

The canonical ignored runtime artifacts exist in:

- `/mnt/hdd-data/home/l4nd0/tenn/reports/ops_checks/nightly`
- `/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite`
- `/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news.sqlite`

This task explicitly authorizes using those canonical ignored artifact paths as live data inputs/outputs, with backups, while keeping source code and tracked repo files untouched.

Known issue:
- 2am cron fired on May 13 and May 14.
- newspaper4k fetch succeeded:
  - May 13 fetched 189 / inserted 141
  - May 14 fetched 190 / inserted 140
- `news_articles.sqlite` newest fetched data was previously reported as `2026-05-13T16:46:29Z`.
- Downstream sync failed both latest runs:
  - `qdrant_sync.status = error`
  - Ollama embed returned 500 Internal Server Error
  - `sqlite_fallback.status = not_run`
- `reports/qual_context/news.sqlite` was stale:
  - newest chunk still `2026-05-08T16:07:02Z`
- Recent checks:
  - backend health ok
  - Cockpit health ok
  - Ollama embed ok
  - Qdrant reachable
  - Qdrant `news_chunks`: green, `19227` points

# Required preflight

Run from:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Commands:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_downstream_sync_fallback_live_artifact_repair_v1_20260515.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_downstream_sync_fallback_live_artifact_repair_v1_20260515.md
- claim task if safe

Hard stop if registry claim fails.

# Runtime/Ollama/Qdrant health

Run:

```bash
curl -m 5 -sS http://127.0.0.1:8000/api/health || true
curl -m 5 -sS http://127.0.0.1:8001/health || true
curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health || true
curl -m 10 -sS http://127.0.0.1:11434/api/embed -d '{"model":"nomic-embed-text","input":"tenn news sync smoke"}' || true
curl -m 5 -sS http://127.0.0.1:6333/collections || true
curl -m 5 -sS http://127.0.0.1:6333/collections/news_chunks || true
```

Hard stop if:

- backend/Cockpit/Ollama/Qdrant health needed for sync is down;
- Ollama embed still fails and fallback path is unclear;
- Qdrant is unreachable and sync-only path requires it.

# Canonical live artifact paths

Use these absolute paths:

```bash
NEWS_ARTICLES_DB=/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite
NEWS_CONTEXT_DB=/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/news.sqlite
NIGHTLY_DIR=/mnt/hdd-data/home/l4nd0/tenn/reports/ops_checks/nightly
```

Before any write:

- verify all paths exist;
- record file sizes;
- record SHA256 for both sqlite DBs;
- create timestamped backups under:
  `/mnt/hdd-data/home/l4nd0/tenn/reports/qual_context/backups/`

Backup both:

- `news.sqlite`
- `news_articles.sqlite`

Do not proceed if backups fail.

# Read-only inspection first

Inspect:

- `financial-engine_v2/scripts/nightly_news.sh`
- `financial-engine_v2/worker/worker_app/celery_app.py`
- `financial-engine_v2/worker/worker_app/news_tasks.py`
- `scripts/load_news_to_qdrant.py`
- latest files under `$NIGHTLY_DIR`

Run SQLite freshness queries before any sync:

For `$NEWS_ARTICLES_DB`:

- table list
- article count
- newest article timestamp
- rows for May 13-15 if schema supports it

For `$NEWS_CONTEXT_DB`:

- table list
- chunk count
- newest chunk timestamp
- chunks for May 13-15 if schema supports it

Run Qdrant read-only checks:

- `news_chunks` collection status
- total points
- any payload freshness fields available
- do not create indexes
- do not delete points

# Allowed work

You may run the existing downstream-only command if clearly scoped.

Expected command shape discovered earlier:

```bash
python3 scripts/load_news_to_qdrant.py \
  --since-hours 36 \
  --refresh-sqlite-fallback \
  --memo-diagnostics-path financial-engine_v2/data/reports/research_memory/news_memos.jsonl \
  --summary-json <new-summary-json-path>
```

Use absolute DB paths if the script supports env vars or flags. If it only uses repo-relative paths, then run it from `/mnt/hdd-data/home/l4nd0/tenn` because that checkout contains the ignored runtime artifacts.

Important:

- Running from preserve checkout is allowed only for this existing data command.
- Do not edit preserve checkout source code.
- Do not commit anything from preserve checkout.
- Record exact cwd and command.
- Keep scope latest 36-48h only.
- Do not run broad refetch/backfill.

# Explicitly forbidden

Do not:

- broad-refetch newspaper4k
- all-time backfill
- wipe/recreate Qdrant collection
- delete Qdrant points
- create Qdrant indexes unless separately approved
- change embedding model
- edit entity linker
- edit ranking/synthesis/source-label/QueryOrchestrator code
- edit news source code
- mutate Financial Truth
- mutate company memory
- restart runtime
- run Docker build
- commit DB files
- commit source code
- run destructive cleanup

# Decision logic

If a safe sync-only command exists:

- run it for latest 36-48h only.
- record exact command.
- backup first.

If only broad refetch/backfill exists:

- do not run it.
- report command gap and proposed future implementation task.

If Qdrant sync succeeds but `news.sqlite` remains stale:

- classify fallback behavior.

If Ollama embed fails again:

- prove whether fallback should run and why it did or did not.

If everything is already fresh:

- report verified no-op.

# Required validation after action

Run:

- SHA256 after for both DBs
- SQLite freshness for `$NEWS_ARTICLES_DB`
- SQLite freshness for `$NEWS_CONTEXT_DB`
- Qdrant `news_chunks` collection status
- Qdrant points count
- counts of synced chunks/articles for latest 36-48h if available
- existing verifier if path works:
  `python3 scripts/verify_news_context_db.py --db "$NEWS_CONTEXT_DB"`
- compare before/after freshness
- confirm no source code changed:
  `git -C /home/l4nd0/tenn-fast-dev-storage-v1 status --short --untracked-files=all`
  `git -C /mnt/hdd-data/home/l4nd0/tenn status --short --untracked-files=all`
  `git diff --check` in active NVMe
- task-card check-diff
- registry release/list-active

# Hard stops

Stop and report if:

- canonical artifact paths are missing
- backups fail
- no safe sync-only command exists
- command would affect all historical news
- Qdrant wipe/recreate/delete is required
- source code changes would be required
- DB state looks inconsistent
- runtime dependencies are down
- dirty tracked source files would be modified
- validation cannot distinguish whether freshness improved

# Commit rules

Commit only task card/report artifacts in active NVMe worktree. Do not commit DB files or source code.

Suggested commit if repaired:

`milestone(query): repair news downstream sync fallback`

Suggested commit if blocked/no-op:

`milestone(query): audit news downstream sync fallback live artifacts`

# Final report

Write:

`reports/agent_jobs/news_downstream_sync_fallback_live_artifact_repair_v1_20260515/README.md`

Include:

- verdict: repaired / verified stale / blocked / partial / no-op
- branch / HEAD / worktree
- exact data paths used
- backup paths/SHA256
- runtime/Ollama/Qdrant health
- before/after freshness:
  - `news_articles.sqlite`
  - `news.sqlite`
  - Qdrant `news_chunks`
- exact sync/fallback command run, if any
- sqlite fallback behavior
- May 10-12 DATA_MISSING status
- validation results
- source-code git status for active NVMe and preserve checkout
- final git status
- registry release/list-active status
- recommended next step
- Project Memory save recommendation
