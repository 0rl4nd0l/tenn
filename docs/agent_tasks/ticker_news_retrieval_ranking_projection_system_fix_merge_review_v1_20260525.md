---
job_id: ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/merge_review.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/smoke_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525/diff_review.md
  - docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/pre_fix_ticker_matrix.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/news_path_map.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/root_cause_trace.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_ticker_matrix.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_smoke_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/diff_review.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/rag.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - financial-engine_v2/backend/tests/test_rag_news_query.py
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525
mutation_mode: safe_extension
requested_mutation_mode: merge_review_integration
production_data_access: false
---

# Ticker News Retrieval Ranking Projection System Fix Merge Review

Merge-review and safe-integration task for parked commit
`9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1` from branch
`safe/ticker-news-retrieval-ranking-projection-system-fix-v1-20260525` into
canonical `migration/clean-runtime-baseline-reconstruct-v1`.

The repo task-card validator supports `safe_extension`, so this card uses that
repo-native mode and records the requested merge-review integration intent in
`requested_mutation_mode`.

## Objective

Review the parked ticker-news retrieval, ranking, and source-pack fix as a
merge-review queue item. If it is still valid, conflict-free, in scope, and
validation passes, integrate it into canonical with cherry-pick provenance.
Then run focused validation and backend-only changed-code live smoke when safe.

## Allowed Scope

The allowed integration files are limited to this merge-review task card and
report bundle plus the exact files changed by parked commit
`9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1`.

## Forbidden

- DB mutation
- Qdrant mutation
- news-store mutation
- reindex, resync, backfill, projection rebuild, or projection repair
- migrations
- parser routing changes
- canonical financial truth writes
- Tenn memory writes, cleanup, or canonicalization
- runtime, model, GPU, Docker, systemd, cron, env, or volume config edits
- broad UI redesign
- one-off ticker alias hardcoding
- weakening `chat_evidence_guard.py` or the landed local-news honesty guard
- allowing filings, documents, or price context to satisfy local-news claims
- hiding degraded runtime states
- relabelling `context_only`, no-hit, or degraded evidence as verified
- relaxing tests to accept dishonest source-grounding
- cleaning, stashing, resetting, deleting, or committing unrelated files
- committing unrelated task cards unless separately authorized

## Required Preflight

1. Record canonical branch, HEAD, worktree path,
   `git status --short --untracked-files=all`, worktree list, and recent
   commits.
2. Verify parked worktree HEAD, status, commit stat, and exact file list.
3. Read the parked report artifacts.
4. Confirm current canonical contains
   `173a8750caa4602e5791ee072673db17e708c5d3` or a descendant with the same
   source-grounding guard.
5. Validate this task card, list active registry entries, check overlap, and
   claim only if safe.
6. Classify known canonical foreign task cards without touching them:
   `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
   and
   `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`.
7. Use a clean isolated integration worktree if canonical dirty state would
   block task-card overlap or diff checks.

## Merge Review Gates

- Confirm changed files from parked commit are within allowed scope.
- Confirm no forbidden surfaces were touched.
- Confirm no DB/Qdrant/news-store mutation, reindex, resync, backfill,
  projection repair, parser routing, memory writes, financial truth writes,
  runtime/model/GPU config edits, broad UI redesign, or one-off ticker alias
  hardcoding.
- Confirm the landed local-news honesty guard remains intact.
- Confirm target branch drift since parked base does not invalidate the fix.
- Stop if conflicts require files outside this card.

## Integration

Prefer:

`git cherry-pick -x 9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1`

Do not squash away provenance. Do not merge unrelated parked work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525.md`
- JSON validation for report artifacts
- `python3 -m py_compile` for changed backend Python files
- Ruff for changed backend Python files and tests
- focused ranking/source-pack tests
- guard/status/source/route parity suite
- Cockpit chat stream suite
- existing local-news honesty guard tests
- existing news status tests
- existing route parity/source-label tests
- `git diff --check HEAD~1..HEAD`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_merge_review_v1_20260525.md --no-write-report`
- Architecture review for forbidden mutation, source-label masking, runtime
  config edits, one-off hardcoding, and honesty-guard weakening

## Changed-Code Live Smoke

If integration succeeds and tests pass, inspect current backend runtime. Restart
only `fe_backend` / backend if the local project-standard backend-only command
is available and required to serve the integrated code. Do not restart Qdrant,
Postgres, workers, GPU workers, llama-server, Next, or unrelated services.

Run read-only stateless probes for:

- A2M local-news/news-intent
- at least two non-A2M tickers with local evidence from the report basket
- one no-local-news/control ticker
- one SSE smoke if safe and already covered by route/test support

Record request body, status, latency, source coverage, claim-verified count,
local-news context count, source labels, source-pack local news presence, final
text alignment, DATA_MISSING behavior, document/filing/price separation,
degraded warnings, restart command if any, and PASS/PARTIAL/FAIL/DATA_MISSING.

## Required Report Bundle

- `README.md`
- `status.json`
- `merge_review.json`
- `validation_results.json`
- `smoke_results.json` if live smoke runs
- `diff_review.md`

## Definition Of Done

Done means one of:

- MERGED_AND_VALIDATED: parked commit integrated into canonical, focused
  validation passes, changed-code live smoke passes or honestly reports
  `DATA_MISSING`, no forbidden mutation occurred, and reports are complete.
- MERGED_BUT_LIVE_SMOKE_BLOCKED: integration and tests pass, but live smoke
  requires unavailable or unsafe runtime action, with exact next smoke command.
- PARKED_STILL or BLOCKED_WITH_PROOF: integration is not safe, branch remains
  frozen, and exact blocker plus next merge-review path are reported.
