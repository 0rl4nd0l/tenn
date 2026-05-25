---
job_id: confirmed_metric_extracted_payload_scoring_audit_v1_20260525
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/confirmed_metric_extracted_payload_scoring_audit_v1_20260525.md
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/README.md
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/status.json
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/extracted_payload_inventory.json
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/scoring_availability.json
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/validation.json
  - reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #63: confirmed metric extracted-payload scoring availability.

# Scope

Determine whether current confirmed metric coverage can be scored against existing extracted payload artifacts without running production extraction or mutating parser, fixture, gold, canonical truth, source PDF, DB, Qdrant, news, or memory surfaces.

# Hard Boundaries

- Do not run production extraction, ingestion, backfill, reindex, or source PDF regeneration.
- Do not mutate parser routing, extraction prompts, scorecard code, gold labels, fixture labels, canonical financial truth, production DB, Qdrant, source PDFs, news stores, or memory stores.
- Do not promote candidate rows.
- Do not promote ambiguous or derived rows.
- Do not combine `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` denominators.
- Do not claim broad extraction accuracy.
- Mutate only this task card and listed report artifacts.

# Required Outputs

- Source-PDF resolution report references.
- Confirmed metric scoring-gap report references.
- Extracted payload artifact inventory.
- Profile-specific scoring availability.
- `DATA_MISSING` where payloads are absent.
- No-regression/canonical-truth boundary statement.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, current artifact inventory commands, JSON validation, `git diff --check`, and task-card check-diff.
