---
job_id: chat_ticker_intent_misclassification_audit_v1_20260602
title: Chat ticker intent misclassification audit
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Evaluation
mutation_mode: audit_only
approval_required: false
production_data_access: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602
github_comment_targets:
  - 119
allowed_files:
  - docs/agent_tasks/chat_ticker_intent_misclassification_audit_v1_20260602.md
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/README.md
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/status.json
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/ticker_probe.json
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/root_cause.md
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/validation.json
  - reports/agent_jobs/chat_ticker_intent_misclassification_audit_v1_20260602/diff-check.json
---

# Chat Ticker Intent Misclassification Audit

## Objective

Audit GitHub issue #119, where the Cockpit chat prompt prefix `UI_AUDIT_GEMINI` was interpreted as ticker `UI` and led to a `daily_news_ingest` proposal.

This is audit-only. Do not implement product remediation in this task.

## Allowed Work

- Inspect ticker intent and chat routing code read-only.
- Run deterministic local probes against pure Python ticker detection helpers.
- Run focused existing tests when available.
- Produce report artifacts under the output directory.
- Comment on issue #119 with the report and PR link after validation.

## Forbidden Work

- No production DB, Qdrant, news, memory, company memory, market memory, or thesis memory writes.
- No ingestion, backfill, refresh, or `daily_news_ingest` execution.
- No canonical financial truth, parser routing, extraction prompt, gold label, model, runtime, GPU, or service config changes.
- No product code or UI changes.
- No one-off heuristic suppression that could break explicit ticker queries.

## Required Evidence

- Classify why `UI_AUDIT_GEMINI` can become ticker `UI`.
- Identify the code path and tests that currently govern this behavior.
- Probe audit/session-marker prompts and explicit ticker prompts.
- Preserve explicit ticker-routing remediation requirements as follow-up guidance.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_ticker_intent_misclassification_audit_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_ticker_intent_misclassification_audit_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_ticker_intent_misclassification_audit_v1_20260602.md`
- focused ticker/chat tests when available
- JSON validation for generated artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_ticker_intent_misclassification_audit_v1_20260602.md`

## Done Criteria

- Root cause is documented with current-turn code/probe evidence.
- Product remediation is either explicitly deferred with blockers or scoped as a safe follow-up.
- Issue #119 remains open unless a valid close gate is later satisfied by separate remediation.
- No forbidden surfaces are changed.
