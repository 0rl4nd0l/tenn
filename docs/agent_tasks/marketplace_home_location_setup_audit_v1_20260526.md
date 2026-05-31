---
job_id: marketplace_home_location_setup_audit_v1_20260526
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526
production_data_access: false
allow_audit_code_changes: false
github_mutation_allowed: false
issue_number: 117
allowed_files:
  - docs/agent_tasks/marketplace_home_location_setup_audit_v1_20260526.md
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/**
allowed_repo_files:
  - docs/agent_tasks/marketplace_home_location_setup_audit_v1_20260526.md
  - reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/**
forbidden:
  - product/backend/frontend/runtime code changes
  - production DB/Qdrant/news/memory
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - runtime/model/GPU/service config
  - persistent preference/storage changes
  - unrelated dirty work
---

# Marketplace Home Location Setup Audit

## Objective

Audit whether `No home location saved` materially blocks Marketplace mission
creation or whether current Settings/default-location and per-mission location
paths are sufficient.

## Required Outputs

- `reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/README.md`
- `reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/status.json`
- `reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/location_contract_matrix.json`
- `reports/agent_jobs/marketplace_home_location_setup_audit_v1_20260526/validation.json`

## Validation

- Controller task-card validate/check-diff.
- Read-only source/static inspection.
- Existing browser-audit artifact inspection.
- Focused backend marketplace tests where available.
- Duplicate issue search.
- `git diff --check`.
