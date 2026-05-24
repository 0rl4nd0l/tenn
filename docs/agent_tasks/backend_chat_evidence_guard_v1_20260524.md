---
job_id: backend_chat_evidence_guard_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md
  - reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/
  - reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/README.md
  - reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/diff-check.json
  - reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/status.json
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/backend_chat_evidence_guard_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Backend Chat Evidence Guard

Audit-first safe-extension task to add deterministic backend evidence guards so
unsupported market, technical, metric, or context-only claims are prevented from
being silently presented as verified Cockpit chat evidence.

## Scope

- Primary lane: Query Orchestration.
- Supporting lanes: Provenance, Reporting, Evaluation.
- Backend-first metadata/test changes are preferred.
- Frontend changes are allowed only for minimal compatibility with backend
  metadata.

## Required Boundaries

- Do not mutate data stores, runtime, extraction truth, memory, Qdrant/news,
  Docker, cron, model/GPU config, parser routing, or canonical financial truth.
- Do not hard-code CSL-only behavior.
- Do not weaken evidence labels or hide degraded runtime state.
- Stop if the implementation requires production data, retrieval ranking
  changes, broad prompt architecture rewrites, or live store mutation.

## Required Regression Seed

Generic CSL-style fixture:

- filing-only sources such as buy-back notices and tariff filings;
- no market/price/technical evidence;
- no extracted financial metrics;
- an attempted bearish/bullish/technical price-trend answer;
- expected backend metadata includes market-data missing or unsupported/not
  verified state rather than claim-verified state.

## Validation

- Validate this task card.
- Check and claim the registry before implementation if overlap is safe.
- Run focused backend compile/test validation for changed files.
- Run frontend validation only if frontend files change.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Write the final report under
  `reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/`.
