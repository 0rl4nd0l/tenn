# Status Route Contract Implementation For News Health

## Executive Result

Implemented a bounded read-only backend status contract for A2M/news health:
`GET /api/cockpit/news/status`. The route reports the split truth without
changing retrieval behavior or mutating Qdrant, SQLite, Postgres, news stores,
chat/session state, projection builders, aliases, source labels, parsers, or
runtime configuration.

## Confirmed

- `/home/l4nd0/tenn` resolves through `/home/l4nd0/tenn-runtime` to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Work started from `af49ede4ceb0e809580efe97754d9f17fbcd3c50` on
  `migration/clean-runtime-baseline-reconstruct-v1`.
- Shared-checkout `check-overlap` was blocked by two foreign untracked task
  cards, so implementation moved to isolated branch
  `safe/status-route-contract-news-health-v1-20260525`.
- Current `/rag/query` exists and dispatches `source="news"` to Qdrant-backed
  `query_news_chunks`.
- Current Cockpit News UI searches through `/rag/query`.
- Backend `/api/cockpit/health` and `/api/cockpit/config` exist but did not
  expose the A2M/news projection split.
- `/api/news/status` remains intentionally absent in the current route-parity
  profile.
- New focused tests pass for `/api/cockpit/news/status` and the existing
  route-parity contract.

## Inferred

- Next.js same-origin `/api/cockpit/news/status` can reach the backend status
  route through the existing `/api/:path*` rewrite when the backend is reachable.
- A separate explicit Next BFF file is not required for this contract because
  the current app already rewrites `/api/*` to the backend.

## Speculative

- A future UI consumer could render this route in Cockpit News or status/config
  panels. No UI consumer was added in this task to avoid colliding with active
  Reporting work and closed UI issue scope.

## DATA_MISSING

- Live chat synthesis for an A2M prompt remains `DATA_MISSING`; no chat/session
  smoke was run.
- Live Qdrant was not probed by the new status route; it reports the integrated
  read-only smoke evidence and marks `live_qdrant_probe_performed=false`.
- Legacy SQLite files were not opened by the new status route; it reports prior
  read-only smoke evidence and marks `live_legacy_db_read_performed=false`.
- `.cursor/rules/` was absent in this checkout, so architecture review used the
  repo architecture docs instead.

## Branch And HEAD

- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Working branch: `safe/status-route-contract-news-health-v1-20260525`
- HEAD before implementation: `af49ede4ceb0e809580efe97754d9f17fbcd3c50`
- HEAD after implementation: `COMMITTED_SEE_TERMINAL_CLOSEOUT`

## Registry State

- Initial shared-checkout overlap: blocked by unrelated dirty task cards:
  - `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
  - `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`
- Safe isolation: used.
- Isolated claim: acquired with exact source/test/report allowlist, then
  released after validation.
- Active foreign jobs were preserved and did not overlap the candidate files.

## Closed-Audit Findings Incorporated

- Issue #64 hygiene context prevented overreacting to worktree volume and
  foreign task-card dirt.
- Issue #65 merge-parking audit meant no parking path was assumed.
- Issue #67 Graphify audit meant absent ignored Graphify artifacts were not a
  blocker.
- Closed Cockpit UI issues were treated as unrelated UI/reporting fixes; this
  task did not duplicate or overwrite them.

## Route/Status Contract Result

New route: `GET /api/cockpit/news/status`

The route returns `a2m_news_health` with:

```json
{
  "qdrant_retrieval": "ok",
  "canonical_sqlite_projection": "missing",
  "legacy_sqlite_projection": "evidence_present_not_current_consumer",
  "cockpit_query_route": "ok_via_rag_query",
  "cockpit_status_routes": "implemented",
  "chat_synthesis": "DATA_MISSING",
  "projection_repair": "not_run"
}
```

The canonical SQLite projection value is computed from path presence; current
expected state remains `missing`.

## Implementation Result

Implemented:

- `financial-engine_v2/backend/app/services/news_health_status.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_news_status.py`

Not implemented:

- No projection repair/rebuild.
- No ingestion/backfill/reindex/resync/news refresh.
- No Qdrant or DB mutation.
- No legacy DB copy/symlink.
- No A2M alias, canonicalization, source-label, parser, extraction, metric, UI
  redesign, runtime, Docker, systemd, cron, env, model, GPU, chat/session, or
  filesystem cleanup changes.

## Validation

- Task-card validation: pass.
- Registry `check-overlap`: pass in isolated worktree after allowlist update.
- `python3 -m py_compile` on touched Python files: pass.
- Manual dependency-light contract smoke: pass.
- `uv run --isolated --with ruff==0.15.6 ruff check ...`: pass.
- Focused pytest under isolated Python 3.11 uv environment:
  `financial-engine_v2/backend/tests/test_cockpit_news_status.py` and
  `financial-engine_v2/backend/tests/test_route_parity_contract.py`: 4 passed,
  6 warnings.

## Final Worktree Status

Committed; exact final HEAD is recorded in the terminal closeout because a
commit cannot self-embed its final hash without changing that hash.

## Next Recommended Task

Run a separate projection repair planning audit before any rebuild/repair, or a
separately carded safe chat synthesis smoke if the operator needs proof that
live chat can synthesize A2M. Do not combine those with this status contract.
