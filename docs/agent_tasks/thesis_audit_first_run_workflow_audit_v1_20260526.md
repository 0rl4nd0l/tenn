---
job_id: thesis_audit_first_run_workflow_audit_v1_20260526
lane: Reporting
supporting_lanes:
  - Provenance
  - Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526
production_data_access: false
allow_audit_code_changes: false
github_mutation_allowed: false
issue_number: 118
allowed_files:
  - docs/agent_tasks/thesis_audit_first_run_workflow_audit_v1_20260526.md
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/**
allowed_repo_files:
  - docs/agent_tasks/thesis_audit_first_run_workflow_audit_v1_20260526.md
  - reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/**
forbidden:
  - product/backend/frontend/runtime code changes
  - production DB/Qdrant/news/memory
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - runtime/model/GPU/service config
  - invented thesis claims or fake audit evidence
  - unrelated dirty work
---

# Thesis Audit First-Run Workflow Audit

## Objective

Audit the first-run Thesis Audit path for report/source selection, coverage
preflight, provenance labels, and evidence-limited behavior.

## Required Outputs

- `reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/README.md`
- `reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/status.json`
- `reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/first_run_matrix.json`
- `reports/agent_jobs/thesis_audit_first_run_workflow_audit_v1_20260526/validation.json`

## Validation

- Controller task-card validate/check-diff.
- Read-only source/static inspection.
- Existing browser-audit artifact inspection.
- Existing Playwright test inspection and attempted local test execution.
- Duplicate issue search.
- `git diff --check`.
