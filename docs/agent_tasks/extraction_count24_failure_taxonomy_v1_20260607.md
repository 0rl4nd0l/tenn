---
job_id: extraction_count24_failure_taxonomy_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
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
output_dir: reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
---

# Count-24 Failure Taxonomy Audit

## Objective

Audit the 16 failed documents from the bounded count-24 validation and identify
the next narrow repair path.

## Scope

Mode: AUDIT FIRST. SAFE EXTENSION only if the failure evidence supports one
narrow, source-bound, tested fix.

Risk: MEDIUM/HIGH.

## Hard Stops

- Do not rerun count-24.
- Do not run count-32.
- Do not run broad extraction or backfill.
- Do not mutate DB, Qdrant, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, or production data.
- Do not loosen validation gates or add broad fuzzy exclusions.
- Do not perform unrelated cleanup, reset, stash, merge, or branch deletion.

## Required Evidence

- Count-24 sample manifest.
- Count-24 sample results.
- Count-24 classification artifact.
- Count-24 side-effect audit.
- Count-24 validation artifacts.

## Required Output

- Failed-document table for all 16 failures.
- Failure buckets and repeated root causes.
- Decision on whether one narrow repair is justified.
- Exact next repair prompt if no code fix is made.
- Validation evidence and explicit no-sample/backfill statement.
