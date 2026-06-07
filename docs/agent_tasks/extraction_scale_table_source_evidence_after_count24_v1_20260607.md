---
job_id: extraction_scale_table_source_evidence_after_count24_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_scale_table_source_evidence_after_count24_v1_20260607.md
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/README.md
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/mqr_integration_audit.json
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/source_evidence.json
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/root_cause_classification.json
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/repair_decision.json
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/status.json
  - reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/validation.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/README.md
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/harness_manifest.json
  - reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/decision.json
  - reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/failed_documents.json
  - reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/failure_taxonomy.json
  - reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/repair_decision.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
---

# Scale Table Source Evidence After Count-24

## Objective

Preserve the local MQR `results-of-meeting` source-noncandidate fix if clean,
then audit WHC, AZJ, EDU, and NIC scale/table/source evidence from the fixed
post-count24 harness without running another sample.

## Scope

Mode: RESULT REVIEW + TARGETED AUDIT. SAFE EXTENSION only if the same
source-bound repair pattern appears in at least two audited harness cases.

Risk: HIGH for financial truth.

## Hard Stops

- Do not rerun count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, or production data.
- Do not merge dirty parent batches.
- Do not clean, stash, reset, or delete unrelated dirt.

## Required Evidence

- Local MQR commit `b5537f933f2b7b31a1cab8dea0f4204ba2ac8360`.
- Regression-consolidation harness manifest.
- Count-24 failure taxonomy artifacts.
- Read-only source text/table-header inspection for WHC, AZJ, EDU, and NIC.

## Required Output

- MQR local fix status.
- WHC/AZJ/EDU/NIC evidence table.
- Root-cause classification.
- Repair decision and any fix/tests made.
- Validation and explicit no-sample/backfill statement.
