---
job_id: asxfp_10_restatement_precedence_v1_20260730
title: Implement evidence-backed ASX financial observation supersession
lane: Financial Truth
supporting_lanes:
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: 'Owner authorized the parent goal with "3 /goal use codex x to complete the rest of the tickets" before the delivery branch existed and explicitly requested Ticket 10 implementation.'
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_10_restatement_precedence_v1_20260730
closeout_scope: local_commit
allowed_files:
  - docs/agent_tasks/asxfp_10_restatement_precedence_v1_20260730.md
  - financial-engine_v2/backend/app/alembic/versions/0014_observation_supersessions.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/models/financial_observations.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_10_restatement_precedence_v1_20260730/README.md
docs_impact: TASK_CARD_AND_REPORT_ONLY
docs_checked:
  - docs/extraction/metric_extraction_contract.md
docs_changed:
  - docs/agent_tasks/asxfp_10_restatement_precedence_v1_20260730.md
  - reports/agent_jobs/asxfp_10_restatement_precedence_v1_20260730/README.md
docs_followup: NONE
reason: "Ticket 10 adds a narrow persistence and read-precedence contract without changing extraction guidance."
task_tier: standard
---

# ASXFP Ticket 10 — restatement precedence

## Objective

Add an immutable, evidence-backed supersession relationship between accepted
statutory observations. Active financial profile reads must exclude only
explicitly superseded observations, prefer the unique restated observation,
and retain provenance-bearing history.

## Authority

- Base commit: `ba0688af97cdcaaf9cf21a0dddc2c1ba5aca2a33`
- Base tree: `4ec31edc8a2b43dd6d700fc4626acbc42d9cbc6b`
- Rejected repair head:
  `d98a4d9543c8979d98c66f550d2da745bd3e521b`
- Rejected repair tree:
  `69aef37e7582c842a97efef7dc1aebe55b823043`
- Ticket 10 SHA-256:
  `c025e1d2e05a89e8e8c99577e6479283c8377fc632fc308b3b7634938873e9a0`

## Bounded rejected-review repair

- Derive active precedence from validated supersession topology, retaining
  terminal restatements when unrelated ordinary observations arrive later.
- Reuse deterministic observations after conflict-free retry inserts so the
  existing candidate can still stage its supersession edge without changing
  the public staging return contract.
- Align migration and ORM index names and prove the full focused schema
  contract.
- Enforce supersession relationship and evidence immutability in PostgreSQL
  with a mutation-rejecting trigger.
- Protect `/financials/history` with the established API-key dependency and
  prove unauthorized rejection, authorized availability, and static route
  order.
- Derive history `active` flags from the same validated topology terminals as
  the projections, so a later unrelated ordinary observation remains
  queryable but is not mislabeled active.

The repair remains within the original seven-path allowlist.

## Forbidden actions

- No PDF, protected corpus, metadata corpus, or diagnostic corpus access.
- No extraction, OCR, models, evaluation, runtime, service, database,
  migration execution, queue, GPU, deployment, activation, or production write.
- No commit in this isolated run; the root orchestrator transfers the reviewed
  delta. No push, publish, PR mutation, or merge.
- No file outside `allowed_files`.

## Validation

- Static compilation and migration/model contract inspection.
- Focused fake-only observation service and route tests in a disposable
  dependency environment.
- `git diff --check` and exact allowlist audit.
