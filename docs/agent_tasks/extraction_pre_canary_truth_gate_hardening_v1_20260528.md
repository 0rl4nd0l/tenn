---
job_id: extraction_pre_canary_truth_gate_hardening_v1_20260528
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pre_canary_truth_gate_hardening_v1_20260528.md
  - reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528/README.md
  - reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528/status.json
  - reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528/diff-check.json
  - reports/agent_jobs/extraction_second_canary_failure_taxonomy_audit_v1_20260527/**
  - reports/agent_jobs/extraction_canary_output_exposure_audit_clv_ctm_v1_20260527/**
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/**
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/app/services/pipeline_service.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/test_extraction*.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval*.py
  - financial-engine_v2/backend/tests/test_pipeline*.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528
mutation_mode: safe_extension
requested_mutation_mode: audit_first_narrow_pre_persistence_guard_hardening
production_data_access: false
allow_unapproved_safe_extension: true
---

# Extraction Pre-Canary Truth Gate Hardening

## Objective

Harden pre-persistence financial truth gates before any third #96 canary batch,
using the second-canary failure taxonomy, CLV/CTM exposure audit, and CLV/CTM
containment evidence.

The task is audit first. Only narrow source-bound guards may be implemented when
they are local, deterministic, testable, and prefer failed extraction/abstention
over inference.

## Scope

Primary lane: Financial Truth.

Supporting lanes: Evaluation, Provenance, Query Orchestration.

Base evidence:

- Second canary failure taxonomy:
  `reports/agent_jobs/extraction_second_canary_failure_taxonomy_audit_v1_20260527/`
- CLV/CTM exposure audit:
  `reports/agent_jobs/extraction_canary_output_exposure_audit_clv_ctm_v1_20260527/`
- CLV/CTM containment:
  `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/`

## Required Audit Questions

1. Where can advisory-only documents be blocked before canary selection or
   persistence?
2. Where can metric-label mismatch be detected before persistence, especially
   EBITDA being written as EBIT?
3. Where can period/source mismatch be detected before persistence, especially
   annual report source written as `H`?
4. Where can scale sanity checks catch over/under-scaled values before rows are
   written?
5. Which guards should be report-only diagnostics first, and which can safely
   block persistence now?
6. What tests prove these guards block CLV/CTM-like cases without weakening valid
   extraction?

## Hard Stops

- Do not run a third canary batch.
- Do not run broad backfill.
- Do not perform production DB writes.
- Do not perform direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, or commit source PDFs.
- Do not change parser routing.
- Do not change extraction prompts.
- Do not mutate gold labels.
- Do not change runtime, model, or GPU config.
- Do not restart services.
- Do not implement Cockpit UI.
- Do not add schema migrations.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase
  operations.

## Safe Extension Rules

Allowed implementation is limited to pre-persistence guard code and focused tests
that:

- use explicit source text, row references, source period phrases, or payload
  values already present in the extraction run;
- fail or abstain instead of correcting, inferring, or broad-normalizing values;
- block CLV/CTM-like persistence before DB row upsert and Qdrant embedding
  writes;
- do not change prompts, parser route selection, source assets, gold labels, or
  persisted schema.

## Validation

- Focused pytest for touched tests.
- `py_compile` for touched Python files.
- `ruff` for touched Python files.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card validation and `check-diff`.
- Confirm no source PDFs staged.
- Registry release and final `list-active --read-only`.
- Final git status.
- Explicitly state that no canary or backfill was run.

## Outputs

- `reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528/README.md`
- `reports/agent_jobs/extraction_pre_canary_truth_gate_hardening_v1_20260528/status.json`

The final report must include exact guards audited/implemented, CLV/CTM failure
class mapping, tests and validation results, whether a third canary batch is
safe/blocked/needs approval, remaining `DATA_MISSING`, no-canary/backfill
statement, and Project Memory save recommendation.
