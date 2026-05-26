# Ticker News Retrieval Ranking Projection Merge Review

## Summary

- Job: `ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525`
- Agent: Codex
- Lane: Query Orchestration
- Integration worktree: `/home/l4nd0/tenn-ticker-news-retrieval-ranking-projection-merge-review-v1-20260525`
- Canonical worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Canonical HEAD before: `9326c200ff187032b934ff9a33bf53e8a6f96181`
- Parked source branch: `safe/ticker-news-retrieval-ranking-projection-system-fix-v1-20260525`
- Parked source commit: `9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1`
- Integrated commit in review branch: `d0ec32437ac517fe4d512990a00437d1043f297a`
- Merge method: `git cherry-pick -x 9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1`

## Decision

Proceeding with integration. The parked worktree was clean, the commit matched
the requested hash, changed files stayed in scope, and the canonical drift since
base `173a8750caa4602e5791ee072673db17e708c5d3` did not touch the parked
retrieval/source-pack files.

The canonical worktree had the two expected unrelated untracked task cards, so
the merge review ran in a clean isolated worktree and will fast-forward
canonical only after validation. The foreign task cards were read and left
untouched.

## Files Integrated From Parked Commit

- `docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/rag.py`
- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- `financial-engine_v2/backend/tests/test_rag_news_query.py`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/README.md`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/diff_review.md`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/news_path_map.md`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_smoke_results.json`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_ticker_matrix.json`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/pre_fix_ticker_matrix.json`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/root_cause_trace.json`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/status.json`
- `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/validation_results.json`

## Review Findings

No blocking merge-review findings.

- No DB, Qdrant, or news-store mutation.
- No reindex, resync, backfill, projection rebuild, projection repair, or migration.
- No parser routing changes.
- No canonical financial truth writes.
- No Tenn memory writes.
- No runtime, model, GPU, Docker, systemd, cron, env, or volume config edits.
- No one-off ticker alias hardcoding in the changed backend files.
- `chat_evidence_guard.py` was not changed by the parked commit.
- `context_only`, no-hit, data-insufficient, missing-required, and degraded rows remain unverified.

## Validation

- Merge-review task-card validate: PASS.
- Parked task-card validate: PASS.
- Registry list/check-overlap: PASS; claim was released after smoke/report
  completion and active jobs list returned empty.
- JSON validation for parked report artifacts: PASS.
- `py_compile` for changed backend Python files: PASS.
- Ruff for changed backend files/tests: PASS.
- Focused ranking/source-pack tests: `65 passed`.
- Guard/status/source/route parity suite: `47 passed, 5 warnings`.
- Cockpit chat stream suite: `62 passed`.
- `git diff --check HEAD~1..HEAD`: PASS.
- Merge-review task-card `check-diff --no-write-report`: PASS for current uncommitted report card state.

## Live Smoke

Canonical was fast-forwarded to `8f2980e917bb46277096a681dc11493cfedde707`.
The running backend was a non-reloading uvicorn process started before that
fast-forward, so I restarted only the Compose `backend` service:

`docker compose -f financial-engine_v2/docker-compose.yml restart backend`

Post-restart health passed, and no Postgres, Qdrant, worker, GPU worker,
llama-server, Next, image rebuild, env/config, volume, DB, Qdrant, or news-store
mutation was performed.

Changed-code smoke results:

- `news for A2M`: PASS, `claim_verified_source_count=4`,
  `source_coverage_status=claim_verified`, labels
  `claim_verified` + `local_news_context`.
- `news for BHP`: PASS, `claim_verified_source_count=5`,
  `source_coverage_status=claim_verified`, labels
  `claim_verified` + `local_news_context`.
- `news for CSL`: PASS, `claim_verified_source_count=5`,
  `source_coverage_status=claim_verified`, labels
  `claim_verified` + `local_news_context`.
- `news for COH`: DATA_MISSING/no-hit control, `claim_verified_source_count=0`,
  labels `context_only`, `no_hit`, `operational_trace`.
- SSE `news for BHP`: PASS, done event returned
  `claim_verified_source_count=5` with local-news sources.

Residual risk recorded: stricter prompts phrased as `Use only
local_news_context...` retrieved local-news rows for A2M/BHP/CSL but still kept
them `context_only`, so the honesty guard returned `DATA_MISSING`. I did not
implement a second fix in this merge-review task because the prompt forbids new
retrieval/ranking work outside direct cherry-pick conflict resolution.

## Forbidden Mutation Attestation

No forbidden mutation occurred. The only runtime action was restarting
`fe_backend` with the command above so the already-integrated canonical code was
served.

## Project Memory Save Recommendation

Save after completion: the safe canonical integration path for this regression
was isolated merge review, cherry-pick with provenance, focused validation, and
backend-only smoke; the code fix remains in `rag.py` and `cockpit_api.py`, not
`chat_evidence_guard.py` or any store repair path.
