---
job_id: asxfp_ticket09_statutory_adjusted_separation_v1_20260730
title: Separate statutory and adjusted results for ASXFP Ticket 09
lane: Financial Truth
supporting_lanes:
  - Extraction
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "Before this delivery branch existed, the owner requested: '3 /goal use codex x to complete the rest of the tickets'. Repository policy independently permits Tier 1 local commits and draft PR delivery."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_ticket09_statutory_adjusted_separation_v1_20260730
closeout_scope: local_commit
allowed_files:
  - docs/agent_tasks/asxfp_ticket09_statutory_adjusted_separation_v1_20260730.md
  - docs/extraction/financial_observation_contract.md
  - financial-engine_v2/backend/app/alembic/versions/0013_financial_result_disclosures.py
  - financial-engine_v2/backend/app/models/__init__.py
  - financial-engine_v2/backend/app/models/financial_observations.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_ticket09_statutory_adjusted_separation_v1_20260730/README.md
docs_impact: DOCS_REQUIRED
docs_checked:
  - docs/extraction
docs_changed:
  - docs/agent_tasks/asxfp_ticket09_statutory_adjusted_separation_v1_20260730.md
  - docs/extraction/financial_observation_contract.md
  - reports/agent_jobs/asxfp_ticket09_statutory_adjusted_separation_v1_20260730/README.md
docs_followup: "None."
reason: "Ticket 09 requires a fail-closed disclosure lane without weakening the Tickets 04-08 observation and projection contracts."
task_tier: standard
---

# ASXFP Ticket 09 statutory/adjusted separation

## Authority

- Exact clean base commit: `9db0cb9a58c0475447f5cde41242e99d0d8cdac2`.
- Authoritative ticket:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/.scratch/asx-financial-profile-extraction-recovery/issues/09-separate-statutory-adjusted-results.md`
  at SHA-256
  `79c319878337c2f8c6b1782c2b734c7a8815d2ef2b9a01ab5405ab8887b0e077`.

## Objective

Admit only explicit consolidated statutory values to canonical financial
observations, retain explicitly labelled non-statutory figures and their
reconciliation evidence in a separate immutable disclosure lane, and abstain
when accounting basis or consolidation scope is ambiguous.

## Required behavior

- Canonical observations require explicit consolidated/statutory field
  evidence and retain the Tickets 05-08 immutable identity and projection path.
- Adjusted, underlying, normalized, and pro-forma values never enter canonical
  observations. They may enter only the disclosure lane with their exact
  source label and source-bound reconciliation evidence.
- Missing, contradictory, or ambiguous accounting basis or consolidation
  scope abstains from both lanes.
- Fake-only end-to-end staging fixtures prove adjusted values cannot replace a
  statutory canonical value.

## Hard stops

- Do not access PDFs or any protected corpus or metadata.
- Do not run extraction, OCR, models, evaluation, runtimes, services,
  databases, migrations, queues, GPUs, deployments, activation, or writes.
- Do not edit outside `allowed_files`.
- Do not push, publish, open a PR, or merge.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket09_statutory_adjusted_separation_v1_20260730.md`
- Focused fake-only pytest for `financial-engine_v2/backend/tests/test_financial_observations.py`.
- Ruff for changed Python when available.
- `python3 -m py_compile` for changed Python.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asxfp_ticket09_statutory_adjusted_separation_v1_20260730.md`.

## Closeout

Report exact changed paths, validation results, prohibited-action compliance,
residual risks, and a review-ready verdict.
