---
job_id: extraction_pr129_ci_test_harness_first_slice_v1_20260529
lane: Evaluation
supporting_lanes:
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md
  - financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py
  - financial-engine_v2/backend/tests/test_streaming_subprocess.py
  - reports/agent_jobs/extraction_pr129_ci_test_harness_first_slice_v1_20260529/README.md
  - reports/agent_jobs/extraction_pr129_ci_test_harness_first_slice_v1_20260529/status.json
  - reports/agent_jobs/extraction_pr129_ci_test_harness_first_slice_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_pr129_ci_test_harness_first_slice_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# PR 129 CI Test-Harness First Slice

## Objective

Reduce inherited CI red on PR #129 without changing extraction runtime behavior,
canonical financial truth, or any production Cockpit route.

This task addresses only the local, reproduced test-harness signature failures:

- `test_cockpit_service_session_threads.py` monkeypatches for
  `_build_chat_controller` do not accept the production method's current
  `llm_client` keyword.
- `test_streaming_subprocess.py` calls `_run_action_subprocess_streaming()`
  without the now-required `job_id` keyword.

## Lane

Primary lane: Evaluation.

Supporting lanes: Query Orchestration and Reporting because the failing tests
cover Cockpit chat/session and action-job streaming behavior.

## Execution Mode

SAFE EXTENSION MODE, test-harness only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-real-gold-corpus-baseline-v1-20260529`

Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`

Related PR: #129

Related issue: #96

Intended files: this task card, two failing test files, this task's report
bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none. Production contested Cockpit/backend files
are intentionally not modified.

Collision risk: LOW after registry overlap check and claim because the touched
files are tests/report artifacts only.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Evaluation/test harness only.

Relevant contract rules: backend remains authoritative; Cockpit remains a
client/orchestration layer; test fixes must not introduce fallbacks or alter
runtime semantics; extraction evaluation evidence must remain source-bound.

What must not change: runtime reload, canary execution, `POST
/api/process/document/{document_id}`, broad extraction/backfill, DB/Qdrant/news
/memory stores, source PDFs, parser routing, extraction prompts, production
schemas/migrations, model/GPU/service config, production Cockpit code, and
GitHub issue/PR state except status comments if needed.

Why safe: the task updates stale test doubles to match existing production
signatures and supplies deterministic test-only job ids for a helper whose
production callers already pass `job_id`. It does not change production logic.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run runtime reload.
- Do not call `POST /api/process/document/{document_id}`.
- Do not run broad extraction or backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, memory, or canonical financial truth stores.
- Do not edit, move, copy, delete, hash-rewrite, or commit source PDFs.
- Do not edit production Cockpit/backend runtime files.
- Do not change parser routing, extraction prompts, production schemas,
  migrations, runtime/model/GPU/service files, or Cockpit UI.
- Do not close GitHub issues or mark the extraction goal complete.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  branch cleanup operations.

## Required Behavior

- Preserve PR #129 extraction behavior and the BHP real-gold fixture.
- Keep all edits test-only apart from task/report/STATE artifacts.
- Make Cockpit service-session test doubles accept the current
  `_build_chat_controller(..., llm_client=...)` production call shape.
- Make streaming subprocess tests pass deterministic test job ids to
  `_run_action_subprocess_streaming()`.
- Re-run the two failing test files and the focused extraction suite.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md`
- Focused reproduction before fix for at least one Cockpit session-thread test and one streaming subprocess test.
- Focused fixed tests for both touched files.
- Focused extraction guardrail suite from PR #129.
- Targeted Ruff for touched tests.
- `python3 -m py_compile` for touched tests.
- JSON validation for generated report artifacts.
- `git diff --check`.
- Raw source/binary staging scan.
- Sensitive string staging scan.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release extraction_pr129_ci_test_harness_first_slice_v1_20260529 --repo-root .`
- Final PR #129 check status after push.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, files changed, validation run,
PR #129 status, confirmation that no runtime/canary/datastore/source mutation
ran, and the next safe step.
