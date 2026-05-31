---
job_id: source_label_fixture_matrix_v1_20260531
title: Source Label Fixture Matrix v1
owner: Codex
lane: Provenance
primary_lane: Provenance
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Reporting
mutation_mode: safe_extension
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/source_label_fixture_matrix_v1_20260531
allowed_files:
  - docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md
  - financial-engine_v2/backend/tests/test_source_label_fixture_matrix.py
  - cockpit-ui/lib/source-label-fixture-matrix.test.ts
  - reports/agent_jobs/source_label_fixture_matrix_v1_20260531/README.md
  - reports/agent_jobs/source_label_fixture_matrix_v1_20260531/status.json
  - reports/agent_jobs/source_label_fixture_matrix_v1_20260531/validation.json
  - reports/agent_jobs/source_label_fixture_matrix_v1_20260531/diff-check.json
  - reports/agent_jobs/source_label_fixture_matrix_v1_20260531/code_review.json
allow_unapproved_safe_extension: true
---

# Source Label Fixture Matrix v1

Resolve GitHub issue #71 with bounded table-driven source-label fixture coverage
only.

## Scope

- Add backend provenance fixture rows for evidence category and claim
  requirement handling.
- Add frontend fixture rows for Chat actionability and Home source handoff trust
  labels.
- Keep coverage table-driven and explicit across positive and negative source
  label cases.

## Required Fixture Labels

Cover these cases without changing label semantics:

- live source
- historical source
- weak source
- DATA_MISSING
- no-hit
- degraded runtime
- memory context
- external web context
- unknown/unclassified
- direct claim-verified evidence

## Required Boundaries

Do not change:

- source-label semantics;
- canonical financial truth;
- parser or extraction routing;
- extraction prompts;
- gold labels;
- production data;
- DB, Qdrant, news, or memory stores;
- runtime, model, GPU, service, scheduler, or provider config;
- product behavior.

Do not create claim verification from context-only, no-hit, unknown,
snippet-only, memory, external-web, degraded, or unsupported source rows.

## System Contract Compliance

Target system layer: Evaluation coverage for Analysis/Client provenance
behavior. This task does not modify ingestion, extraction, storage, retrieval,
analysis logic, or client product behavior.

Relevant contract rules:

- Backend remains the sole authority for authoritative data and retrieval.
- Cockpit remains a client/orchestration layer only.
- Retrieval, Qdrant, Postgres, canonical financial truth, model usage, and
  runtime topology are not changed.
- No fallback, substitution, duplicate pipeline, or data-store mutation is
  introduced.

GPU guard: not required. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md`
- `PYTHONPATH=financial-engine_v2/backend pytest financial-engine_v2/backend/tests/test_source_label_fixture_matrix.py`
- `cd cockpit-ui && pnpm vitest run lib/source-label-fixture-matrix.test.ts`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md`
- `python3 scripts/agent_job_registry.py release source_label_fixture_matrix_v1_20260531`
