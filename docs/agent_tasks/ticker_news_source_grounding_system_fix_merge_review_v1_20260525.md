---
job_id: ticker_news_source_grounding_system_fix_merge_review_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/ticker_news_source_grounding_system_fix_merge_review_v1_20260525.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/merge_review.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/smoke_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525/diff_review.md
  - docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/blast_radius_matrix.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/root_cause_trace.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/smoke_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/diff_review.md
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_sources.py
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/ticker_news_source_grounding_system_fix_merge_review_v1_20260525
mutation_mode: safe_extension
requested_mutation_mode: merge_review_integration
production_data_access: false
---

# Ticker News Source Grounding System Fix Merge Review

Merge-review and safe-integration task for parked commit
`703d8ada2fccb29f1a77c8a401e1c4fafd046497` from branch
`safe/ticker-news-source-grounding-system-fix-v1-20260525` into canonical
`migration/clean-runtime-baseline-reconstruct-v1`.

The task-card validator supports `safe_extension`, so this card uses that
repo-native mode and records the requested integration intent separately in
`requested_mutation_mode`.

## Objective

Review the parked ticker-universe Cockpit news/source-grounding fix as a
merge-review queue item. If it is still valid, conflict-free, in scope, and
validation passes, integrate it into canonical. Then run focused validation and
changed-code live smoke for the local-news-only source-grounding guard when
safe.

## Allowed Scope

The allowed integration files were confirmed from:

`git -C /home/l4nd0/tenn-ticker-news-source-grounding-system-fix-v1-20260525 diff --name-only 5a6c0c00b58c056fcf93933a9d1dd5754daa3338..703d8ada2fccb29f1a77c8a401e1c4fafd046497`

Only those parked-commit files, this merge-review task card, and this
merge-review report bundle may be changed.

## Forbidden

- DB mutation
- Qdrant mutation
- news-store mutation
- reindex, resync, backfill, projection rebuild, or projection repair
- parser routing changes
- canonical financial truth writes
- Tenn memory writes, cleanup, or canonicalization
- runtime, model, GPU, Docker, systemd, cron, or env config edits
- broad UI redesign
- A2M-only alias hardcoding
- hiding degraded or runtime states
- relaxing tests to accept dishonest source-grounding
- cleaning, stashing, resetting, deleting, or committing unrelated files
- committing unrelated task cards unless separately authorized

## Required Preflight

1. Record canonical branch, HEAD, worktree path,
   `git status --short --untracked-files=all`, worktree list, and recent
   commits.
2. Verify parked worktree HEAD, status, commit stat, and exact file list.
3. Read the parked task card and report bundle.
4. Validate this task card, list active registry entries, check overlap, and
   claim only if safe.
5. Classify known canonical foreign task cards without touching them:
   `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
   and
   `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`.

## Merge Review Gates

- Confirm changed files are within the parked and merge-review allowed scope.
- Confirm no forbidden surfaces were touched by the parked commit.
- Confirm reported validation is still meaningful against current canonical
  HEAD.
- Confirm no active Query Orchestration overlap.
- Confirm target drift from parked base
  `5a6c0c00b58c056fcf93933a9d1dd5754daa3338` and review conflicts before
  integration.
- Stop if conflicts require files outside this card.

## Integration

Prefer:

`git cherry-pick -x 703d8ada2fccb29f1a77c8a401e1c4fafd046497`

Do not squash away provenance. Do not merge unrelated parked work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/ticker_news_source_grounding_system_fix_merge_review_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/ticker_news_source_grounding_system_fix_merge_review_v1_20260525.md`
- JSON validation for report artifacts
- `python3 -m py_compile` for changed backend Python files
- Ruff for changed backend Python files
- focused backend tests:
  - `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
  - `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
  - `financial-engine_v2/backend/tests/test_cockpit_news_status.py`
  - `financial-engine_v2/backend/tests/test_build_ui_sources.py`
  - `financial-engine_v2/backend/tests/test_sources.py`
  - `financial-engine_v2/backend/tests/test_route_parity_contract.py`
- `git diff --check HEAD~1..HEAD`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/ticker_news_source_grounding_system_fix_merge_review_v1_20260525.md --no-write-report`
- Architecture review for forbidden mutation, source-label masking,
  context-only evidence handling, and A2M-only hardcoding.

## Changed-Code Live Smoke

If integration succeeds and tests pass, inspect current backend runtime. Restart
only the backend service if the local project-standard backend-only command is
available and needed to serve the integrated code. Do not restart Qdrant,
Postgres, workers, GPU workers, llama-server, next-server, or unrelated
services.

Run read-only stateless chat smokes for:

- A2M local-news-only
- BHP or CSL local-news-only
- one no-local-news/control ticker, preferably COH if still appropriate

Record request body, status, latency, source coverage, claim-verified count,
local news context count, source labels, final text alignment, DATA_MISSING
behavior, and degraded/runtime/schema warnings.

## Required Report Bundle

- `README.md`
- `status.json`
- `merge_review.json`
- `validation_results.json`
- `smoke_results.json` if live smoke is run
- `diff_review.md` if conflicts or review findings occur

## Definition Of Done

Done means one of:

- MERGED_AND_VALIDATED: parked commit integrated into canonical, focused
  validation passes, changed-code live smoke passes or honestly reports
  `DATA_MISSING`, and no forbidden mutation occurred.
- MERGED_BUT_LIVE_SMOKE_BLOCKED: integration and tests pass, but changed-code
  live smoke requires unavailable service or separate runtime approval, with
  exact next smoke command recorded.
- PARKED_STILL or BLOCKED_WITH_PROOF: integration is not safe, branch remains
  frozen, and exact blocker plus next merge-review path are reported.
