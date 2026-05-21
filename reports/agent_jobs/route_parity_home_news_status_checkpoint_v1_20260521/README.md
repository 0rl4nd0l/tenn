# Route Parity Home / News Status Checkpoint

## Confirmed Facts

- Runtime symlink: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Pre-checkpoint HEAD: `d5fcd71dca27`.
- Source audit task card validation passed after the audit.
- Checkpoint task card validation passed after YAML frontmatter and exact report-child allowlist metadata were added.
- Shared registry was empty before claim: `active_jobs=[]`.
- Shared registry overlap check for this checkpoint task card passed with no issues.
- Registry claim succeeded for `route_parity_home_news_status_checkpoint_v1_20260521`.
- No backend, frontend, Cockpit UI, runtime config, Docker Compose, script, data, DB, SQLite, Qdrant, news store, memory store, source registry, model, parser, extraction, Evaluation Spine, DuckDB, A2M/news retrieval, ASX classifier, sidecar, or dirty HDD preserve worktree source files were changed by this checkpoint.

## DATA_MISSING

- Live listener smoke remains DATA_MISSING from the source audit because no `8000`, `8081`, `3000`, or `3001` services were already running and this checkpoint did not start runtime services.
- Frontend Vitest remains blocked from the source audit because `pnpm` was not on `PATH`.
- This checkpoint did not inspect production data, DBs, Qdrant, news stores, memory stores, Docker volumes, systemd services, model config, CUDA/M40 runtime, parser/extraction surfaces, generated sidecars, canonical truth, or live service payloads.

## Artifacts Preserved

- `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/README.md`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/diff-check.json`
- `docs/agent_tasks/route_parity_home_news_status_checkpoint_v1_20260521.md`
- `reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/README.md`
- `reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/diff-check.json`
- `reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/status.json`

## Force-Add Status

Reports are ignored by default in this worktree. The preserved report files from the audit report directory and the checkpoint report directory are intended to be force-added from only these allowed report paths:

- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/`
- `reports/agent_jobs/route_parity_home_news_status_checkpoint_v1_20260521/`

## Audit Verdict Summary

- `/api/cockpit/home` is intentionally owned by the Next.js BFF.
- Direct backend `/api/cockpit/home` is expected absent and 404 in this branch/profile.
- `/api/news/status` is intentionally absent in this branch/profile.
- Current news retrieval uses `/rag/query`.
- The source audit found stale route expectation/docs-smoke drift only; it did not identify a storage migration blocker.

## Source Audit Validation Summary

- Task-card validate: PASS.
- Registry list-active: PASS, no active jobs.
- Registry overlap check: PASS, no issues.
- Backend route parity pytest: PASS, `2 passed, 5 warnings`.
- Audit `check-diff`: PASS, no disallowed files.
- Audit `git diff --check`: PASS.
- Live listener smoke: DATA_MISSING, services not already running.
- Frontend Vitest: BLOCKED, `pnpm` not found on `PATH`.

## Checkpoint Non-Rerun Statement

This checkpoint did not rerun route tests, live smoke, frontend Vitest, runtime services, backend services, or source changes. It only preserved the completed audit task card and report artifacts and wrote this checkpoint report.

## Checkpoint Validation Summary

- Preflight confirmed runtime path, branch, HEAD, dirty state, ignored report state, worktree list, and current HEAD stat.
- Checkpoint task-card validate: PASS.
- Registry list-active before claim: PASS, `active_jobs=[]`.
- Registry check-overlap before claim: PASS, no issues.
- Registry claim: PASS.
- Checkpoint `check-diff`: PASS, no disallowed files.
- Commit hash: recorded in the final Codex closeout because a Git commit cannot contain its own final hash without changing that hash.
- Registry release: PASS; active record removed after the checkpoint commit.
- Immediate registry list-active after route checkpoint release: PASS, `active_jobs=[]`.
- Later final registry list-active showed one unrelated concurrent job, `strategy_lab_mocked_adapter_design_phase3_v1_20260520`, in a different worktree and lane. The route checkpoint claim remained released.
- Final git status: CLEAN; `git status --short` produced no output after release status was amended into the checkpoint commit.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: preserve that the active NVMe runtime branch checkpointed the 20260521 route parity audit as BFF-owned `/api/cockpit/home`, expected absent backend `/api/cockpit/home`, expected absent `/api/news/status`, and news retrieval via `/rag/query`; this checkpoint did not rerun services or touch source/data/runtime/config surfaces.
