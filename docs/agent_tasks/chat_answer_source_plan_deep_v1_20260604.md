---
job_id: chat_answer_source_plan_deep_v1_20260604
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_answer_source_plan_deep_v1_20260604.md
  - reports/agent_jobs/chat_answer_source_plan_deep_v1_20260604/README.md
  - reports/agent_jobs/chat_answer_source_plan_deep_v1_20260604/status.json
  - reports/agent_jobs/chat_answer_source_plan_deep_v1_20260604/validation.json
  - reports/agent_jobs/chat_answer_source_plan_deep_v1_20260604/diff-check.json
  - financial-engine_v2/backend/app/services/answer_source_plan.py
  - financial-engine_v2/backend/app/services/query_orchestrator.py
  - financial-engine_v2/backend/tests/test_answer_source_plan.py
  - financial-engine_v2/backend/tests/test_query_orchestrator.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/chat_answer_source_plan_deep_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Chat Answer Source Plan Deepening

## Objective

Put answer source ordering, canonical numeric truth, context-only memory, and
missing-data recovery source expansion behind one backend source-plan interface.

## Allowed Implementation

- Add a backend answer-source-plan helper that owns core source roles, source
  ordering, numeric-truth eligibility, context-only memory roles, missing
  category mapping, and bounded recovery expansion.
- Update query orchestration to consume that helper without changing retrieval
  providers, DB/Qdrant access, memory-store contents, embeddings, extraction, or
  runtime services.
- Add focused backend tests proving canonical numbers come only from
  `financial_truth`, memory sources remain context-only, and recovery source
  order is deterministic.

## Forbidden

- No DB, Qdrant, memory-store, financial truth data, runtime-service, embedding,
  extraction, ingestion, schema, or vector changes.
- No promotion of company, market, user thesis, session, or operational memory
  into canonical numeric truth.
- No frontend presentation refactor, browser harness changes, or
  `MultipassResult` contract work in this slice.
- No cleanup or absorption of unrelated worktree dirt from other checkouts.

## Validation

- Validate this task card.
- Check and claim the shared registry before implementation.
- Run focused backend tests for answer source plan and query orchestration.
- Run `git diff --check`.
- Run `check-diff` before closeout.
