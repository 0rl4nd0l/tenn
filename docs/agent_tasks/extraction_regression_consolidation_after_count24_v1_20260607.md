---
job_id: extraction_regression_consolidation_after_count24_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_regression_consolidation_after_count24_v1_20260607.md
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/README.md
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/canonical_history.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/decision.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/failure_family_ledger.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/harness_manifest.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/parking_review.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/status.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/validation.json
  - docs/agent_tasks/extraction_count24_failure_taxonomy_v1_20260607.md
  - reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/**
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/**
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: true
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
---

# Count-24 Regression Consolidation

## Objective

Stop the extraction loop by consolidating current count-24 failures against
prior fixes, parked work, and canonical history. Determine whether the failures
are regressions, unfixed variants, missing integrations, parked-only work, or
expected fail-closed behavior.

## Scope

Mode: REGRESSION CONSOLIDATION / AUDIT FIRST. SAFE EXTENSION only if a repeated
root cause has high-confidence, source-bound evidence and a focused test.

Risk: HIGH for financial truth and repo state.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, or production data.
- Do not merge dirty parent branches.
- Do not clean, stash, reset, or delete unrelated dirt.

## Required Evidence

- Current count-24 bounded validation artifacts.
- Current count-24 failure taxonomy artifacts.
- Merge-parking registry and parked records.
- Recent canonical PR/report history for PR #294, #297, #299, #301, #306, and
  #309 where locally available.

## Required Output

- Repeated-failure ledger by family.
- Canonical versus parked versus missing integration findings.
- Fixed regression harness manifest.
- Decision on high-leverage repair path.
- Final decision enum and next exact prompt.
