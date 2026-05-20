---
job_id: asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
allowed_files:
  - docs/agent_tasks/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520.md
  - docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/extension_point_inventory.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/document_type_classifier_plan.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/deterministic_parser_plan.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/comparator_artifact_plan.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/no_regression_gate_map.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json
  - reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520/
  - reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520/README.md
  - reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520/status.json
---

# ASX deterministic extraction audit artifact checkpoint

## Intent

Preserve the completed ASX deterministic extraction extension audit task card and report artifacts in the active NVMe runtime branch without touching source, runtime, parser, extraction, data, database, model, Cockpit, Docker, environment, or production configuration files.

## Source

- Source worktree: `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519`
- Source branch: `audit/asx-deterministic-extraction-extension-v1-20260519`

## Preserved audit result

- Verdict: `ASX_DETERMINISTIC_EXTENSION_READY_FOR_DESIGN`
- Truth status: `CANONICAL_TRUTH_SAFE`
- Main conclusion: the safe extraction path is fixture/schema-first and comparator-first.

## Required boundaries

- Do not start with parser routing.
- Do not replace Docling.
- Do not promote PyMuPDF.
- Do not treat generic Markdown as truth.
- Do not route comparator output into canonical truth.
- Do not change prompts.
- Do not change gold labels.
- Do not write canonical values.
- Do not use shared `:8001` for strict extraction/eval comparator work.

## Validation plan

- Validate this task card.
- Confirm registry has no overlapping artifact checkpoint or Financial Truth mutation work before claiming.
- Copy only the source ASX audit task card and report files listed in `allowed_files`.
- Reject any staged file outside the task/report artifact allowlist.
- Run `check-diff` and `git diff --cached --check` before committing.
- Commit only the checkpoint task card, ASX audit task card, ASX audit report artifacts, and checkpoint report.
