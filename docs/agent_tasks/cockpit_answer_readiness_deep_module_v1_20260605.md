---
job_id: cockpit_answer_readiness_deep_module_v1_20260605
lane: Query Orchestration
supporting_lanes:
  - Cockpit
  - Evaluation
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_answer_readiness_deep_module_v1_20260605
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
allowed_files:
  - docs/agent_tasks/cockpit_answer_readiness_deep_module_v1_20260605.md
  - financial-engine_v2/cockpit/core/chat.py
  - financial-engine_v2/cockpit/core/answer_readiness.py
  - financial-engine_v2/scripts/test_cockpit_answer_readiness.py
  - financial-engine_v2/scripts/test_cockpit_deep_analysis_grounding.py
  - financial-engine_v2/scripts/test_cockpit_announcement_sync_offer.py
  - financial-engine_v2/scripts/test_cockpit_price_history_chat.py
  - financial-engine_v2/scripts/test_cockpit_chat_ticker_detection.py
  - financial-engine_v2/scripts/test_cockpit_tools_additional_context.py
operator_approval_source: User selected the non-extraction Cockpit answer-readiness architecture slice after noting another agent is working in the extraction lane on 2026-06-05.
---

# Cockpit Answer Readiness Deep Module V1

## Objective

Deepen Cockpit chat answer-readiness architecture without touching the active
extraction lane. Move answer-readiness policy out of the oversized chat
controller into a focused internal module, then lock the current externally
observable behavior with targeted characterization tests.

## Scope

- Map the current Cockpit chat answer-readiness behavior in
  `financial-engine_v2/cockpit/core/chat.py`.
- Centralize evidence sufficiency, announcement freshness decisions, grounded
  fallback construction, and generated-answer rejection policy in
  `financial-engine_v2/cockpit/core/answer_readiness.py`.
- Keep `ChatController.build_chat_response(...)` as the public behavior surface.
- Prefer public-behavior characterization tests over direct private helper
  assertions where practical.
- Preserve honest `DATA_MISSING` behavior when available evidence is missing,
  stale, unverified, or framework-only.

## Hard Stops

- Do not edit extraction code, extraction task cards, extraction docs, gold
  labels, source PDFs, parser routing, canonical metric contracts, prompts,
  DBs, Qdrant, embeddings, backfills, ingestion, runtime bindings, migrations,
  or production data.
- Do not weaken evidence honesty guards, local-news-only guards, or
  `DATA_MISSING` handling.
- Do not introduce synthetic financial truth or fabricated source claims.
- Do not mutate GitHub issues, PRs, or Actions.
- Do not clean, stash, reset, delete, overwrite, or absorb unrelated dirty
  files from the shared checkout.

## Required Preflight

1. Use a clean sibling worktree from the current shared-checkout `HEAD`.
2. Print worktree path, branch, and `HEAD`.
3. Run `git status --short --untracked-files=all`.
4. Validate this task card if repo tooling supports validation.
5. Run registry/list-active and registry/check-overlap if available.
6. Stop if overlap includes extraction-lane files or another active Cockpit
   answer-readiness owner.

## Validation

- Focused pytest for Cockpit answer-readiness tests.
- Existing targeted Cockpit tests touched by the refactor where practical.
- `python -m py_compile` on touched Cockpit core modules if pytest cannot cover
  import validity.
- `git diff --check`.
- `git diff --name-only` must show no extraction-lane files.

## Execution Closeout

- Worktree: `/home/l4nd0/tenn-cockpit-answer-readiness-deep-module-v1-20260605`
- Branch: `safe/cockpit-answer-readiness-deep-module-v1-20260605`
- Base HEAD: `dfa313aa`
- Implemented `financial-engine_v2/cockpit/core/answer_readiness.py` for
  answer-readiness policy and kept `ChatController.build_chat_response(...)`
  as the public behavior surface.
- Updated direct policy tests to use `AnswerReadiness` instead of private
  `ChatController` helpers where practical.
- Added public characterization tests in
  `financial-engine_v2/scripts/test_cockpit_answer_readiness.py`.
- Validation passed:
  `python -m pytest scripts/test_cockpit_*.py -q` returned `84 passed`.
- Validation passed: `python -m py_compile` for touched Cockpit core and test
  modules.
- Validation passed: `git diff --check`.
- Final diff scope contains no extraction-lane file paths.
