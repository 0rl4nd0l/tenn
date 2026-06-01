---
job_id: chat_ticker_intent_misclassification_fix_v1_20260602
title: Chat ticker intent misclassification fix
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602
github_comment_targets:
  - 119
allowed_files:
  - docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md
  - financial-engine_v2/shared/ticker_inference.py
  - financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py
  - financial-engine_v2/cockpit/tests/test_tool_executor.py
  - financial-engine_v2/backend/tests/test_query_orchestrator.py
  - reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602/README.md
  - reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602/status.json
  - reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602/validation.json
  - reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602/diff-check.json
---

# Chat Ticker Intent Misclassification Fix

## Objective

Remediate GitHub issue #119 by preventing ordinary UI/audit/session prose from becoming ticker-scoped merely because it contains a standalone uppercase acronym, while preserving explicit ticker requests.

This follows the audit-only report in `reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/`.

## Allowed Work

- Update the shared ticker detector with a minimal contextual guard for uppercase candidates.
- Add focused regression coverage for the exact Gemini prompt and marker/acronym variants.
- Preserve explicit ticker forms and normal cued ticker queries.
- Produce report artifacts under the output directory.
- Comment on issue #119 after validation.

## Forbidden Work

- No production DB, Qdrant, news, memory, company memory, market memory, or thesis memory writes.
- No ingestion, backfill, refresh, or action execution.
- No canonical financial truth, parser routing, extraction prompt, gold label, model, runtime, GPU, or service config changes.
- No Cockpit UI changes.
- No hidden alias-only fix that breaks explicit ticker routing.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md`
- focused ticker/chat/backend tests
- targeted Ruff on touched Python files
- JSON validation for generated artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md`

## Done Criteria

- Exact Gemini prompt no longer resolves to ticker `UI`.
- Audit/session marker variants with ordinary prose no longer become ticker-scoped.
- `BHP news`, `tell me about csl`, `ASX:UI news`, `$UI news`, and `UI.AX news` still resolve as ticker queries.
- Issue #119 is updated with PR and validation evidence.
- No forbidden surfaces are changed.
