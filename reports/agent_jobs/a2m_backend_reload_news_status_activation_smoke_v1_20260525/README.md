# A2M Backend Reload News Status Activation Smoke

Job: `a2m_backend_reload_news_status_activation_smoke_v1_20260525`
Date: 2026-05-25
Mode: audit-only runtime smoke, backend restart approved
Result: **PARTIAL**

## Scope

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
HEAD: `80284a1560373de0302e5d4f2c4b87be705aa985`
Required commit: `c8d605e3de625c9f456edc0f3896b571a68f6b25` (ancestor of HEAD: `True`)
Task card: `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`

The branch advanced during the audit window from `3a18475b91a325baccd22a3daf07237dc1d3d18b` to `80284a1560373de0302e5d4f2c4b87be705aa985` via unrelated repo-hygiene preservation. This job did not clean, stage, commit, or touch the foreign task cards.

## Registry And Dirt

Initial manual preflight:

- `list-active`: ok, no active jobs
- `check-overlap`: false only because known foreign untracked task cards were dirty outside this card's allowlist
- Active Query Orchestration overlap: none

Known foreign untracked task cards recorded and not touched:

- `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
- `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`

Runtime-collection preflight after the repo-hygiene preservation commit:

- `list-active`: ok
- `check-overlap`: `True`
- Active Query Orchestration overlap: `[]`

Final registry: ok, active jobs = `0`
Final git status: `['?? docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md']`

## Runtime Action

Exact command: `docker compose restart backend`
Command cwd: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`

This restarted only the Compose `backend` service / `fe_backend` process. No image rebuild, dependency restart, DB/Qdrant/news-store mutation, migration, reindex, backfill, projection repair, runtime/model/GPU config edit, or code change was performed.

Post-action service start evidence:

- `fe_backend`: `running`, started_at `2026-05-25T05:51:59.686426623Z`
- `fe_worker`: `running`, started_at `2026-05-25T01:25:18.706349617Z`
- `fe_gpu_worker`: `running`, started_at `2026-05-25T01:25:18.707458848Z`
- `fe_postgres`: `running`, started_at `2026-05-25T01:25:13.106694535Z`
- `fe_qdrant`: `running`, started_at `2026-05-25T01:25:13.103564039Z`

## Route Activation

Pre-reload:

- `GET /api/cockpit/news/status`: `404`
- OpenAPI had `/api/cockpit/news/status`: `False`

Post-reload:

- `GET /api/cockpit/news/status`: `200`
- OpenAPI had `/api/cockpit/news/status`: `True`
- Activated: `True`

Pre-reload OpenAPI evidence: `/api/cockpit/news/status` absent from relevant paths.
Post-reload OpenAPI evidence: `/api/cockpit/news/status` present in relevant paths.

Pre-reload relevant OpenAPI paths include `72` paths; post-reload relevant OpenAPI paths include `73` paths. Full path lists are in `runtime_reload_trace.json`.

## A2M Chat Result

Classification: **PARTIAL**

Source metadata and final synthesis text agree: `False`

- `30s_general_a2m_probe_after_reload`: HTTP `200`, elapsed `15.104`s, source_coverage_status `context_only`, claim_verified_source_count `0`, local_news_context_count `1`, classification `PARTIAL_sources_present_final_text_not_aligned`
- `30s_news_only_a2m_probe_after_reload`: HTTP `200`, elapsed `11.554`s, source_coverage_status `context_only`, claim_verified_source_count `0`, local_news_context_count `1`, classification `PARTIAL_sources_present_final_text_not_aligned`

Both probes returned HTTP 200 and surfaced one `local_news_context` source with `source_coverage_status=context_only` and `claim_verified_source_count=0`, but final text did not align to the returned local-news source.

## Runtime Log Evidence

`cockpit_announcement_context` missing-table error persists after reload: `True`

## Changed Files

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/README.md`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/status.json`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/runtime_reload_trace.json`
- `reports/agent_jobs/a2m_backend_reload_news_status_activation_smoke_v1_20260525/diff-check.json`

## Forbidden Mutation Attestation

Forbidden mutation performed: `false`

No code/data/config/model/GPU changes were made. No DB, Qdrant, news store, memory, canonical financial truth, reindex/resync/backfill, projection repair, parser routing, source-label/ranking/synthesis/prompt/UI fix, or unrelated service restart was performed.

## Validation

- Task-card validation: pass
- JSON validation: pass
- `git diff --check`: pass
- Task-card `check-diff`: pass
- Final registry/list-active: pass, no active jobs
- Final git status: only the allowed untracked task card is visible; report artifacts are under the allowed report directory

## Next Recommended Task

source-grounding trace if synthesis still misattributes sources; runtime/schema audit if missing table persists

## Save Recommendation

Save to Project Memory: Reloading only fe_backend with docker compose restart backend activated /api/cockpit/news/status after c8d605e3 landed; pre-reload OpenAPI lacked the route and returned 404, post-reload OpenAPI included it and GET returned 200. A2M stateless chat still remained PARTIAL because source metadata exposed local_news_context with zero claim-verified sources while final synthesis text did not cleanly align to the local news source. Missing cockpit_announcement_context table errors should be checked by a runtime/schema audit if they persist in logs.
