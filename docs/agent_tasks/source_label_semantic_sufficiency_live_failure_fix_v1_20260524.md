---
job_id: source_label_semantic_sufficiency_live_failure_fix_v1_20260524
title: Source label semantic sufficiency live failure fix
owner: Codex
lane: Provenance
supporting_lanes:
  - Query Orchestration
  - Reporting
  - Evaluation
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
approval_required: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524
allowed_files:
  - docs/agent_tasks/source_label_semantic_sufficiency_live_failure_fix_v1_20260524.md
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/README.md
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/status.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/validation.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/diff-check.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/live_smoke_A_response.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/live_smoke_B_response.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/mutation_snapshot_before.json
  - reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/mutation_snapshot_after.json
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
forbidden:
  - qdrant_mutation
  - postgres_mutation
  - news_store_mutation
  - memory_store_mutation
  - parser_extraction_or_canonical_financial_truth_changes
  - docker_rebuild
  - broad_runtime_topology_change
  - cron_systemd_model_gpu_config_changes
  - retrieval_ranking_rewrite_without_smoke_proof
  - fake_data
  - hiding_data_missing
  - weakening_source_labels
  - unrelated_task_card_cleanup
---

# Source Label Semantic Sufficiency Live Failure Fix

## Objective

Fix the live-path semantic sufficiency gaps exposed by
`source_label_semantic_sufficiency_live_smoke_v1_20260524`.

## Required Investigation

- Trace recent-news/update intent classification and where
  `insufficient_for_recent_news` is expected, dropped, or not rendered.
- Trace financial-truth numeric context wording and where announcement/news/event
  wording enters visible answers.
- Classify root cause before implementation as classifier, metadata propagation,
  synthesis/context, final presentation, frontend rendering, mixed-source label
  ambiguity, or DATA_MISSING visibility gap.

## Implementation Boundaries

- Prefer deterministic backend helper or presentation guard over prompt-only
  wording.
- Recent-news/update/event intent must not be satisfied by price-only,
  `context_only`, broad `local_news_context`, or filing-only evidence unless
  actual event/news evidence is semantically sufficient.
- Financial-truth numeric context must be labelled as numeric record/context
  only, not announcement/news/event verification.
- Preserve existing valid `claim_verified` behavior where evidence is actually
  sufficient.
- Preserve existing visible `DATA_MISSING` guard behavior and source visibility.

## Forbidden

- No Qdrant, Postgres, news, or memory mutation.
- No parser, extraction, or canonical financial truth change.
- No Docker rebuild or broad runtime topology change.
- No fake data, source-label weakening, unrelated task-card cleanup, or hidden
  `DATA_MISSING`.

## Validation

- Validate this task card.
- Registry list-active, check-overlap if supported, claim, release.
- Focused backend pytest for changed evidence/source-label/chat tests.
- Focused frontend/Vitest tests only if terminal-message rendering is touched.
- Focused Ruff on changed Python files.
- TypeScript/ESLint only if frontend is touched.
- JSON validate `status.json`.
- `git diff --check`.
- Task-card `check-diff`.
- If focused tests pass, rerun the two failed stateless live smokes with
  `X-Tenn-Stateless-Smoke: 1` and mutation proof.
