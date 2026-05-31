---
job_id: cockpit_source_drawer_semantics_audit_v1_20260526
lane: Reporting
supporting_lanes:
  - Provenance
  - Query Orchestration
  - Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526
production_data_access: false
allow_audit_code_changes: false
github_mutation_allowed: false
issue_number: 95
allowed_files:
  - docs/agent_tasks/cockpit_source_drawer_semantics_audit_v1_20260526.md
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/**
allowed_repo_files:
  - docs/agent_tasks/cockpit_source_drawer_semantics_audit_v1_20260526.md
  - reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/**
forbidden:
  - product/backend/frontend/runtime code changes
  - production DB/Qdrant/news/memory
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - source-label relaxation
  - runtime/model/GPU/service config
  - unrelated dirty work
---

# Cockpit Source Drawer Semantics Audit

## Objective

Audit whether Cockpit preserves backend source-state distinctions in visible
chat/source UI and report `NO_FOLLOWUP` or a bounded follow-up.

## Required Outputs

- `reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/README.md`
- `reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/status.json`
- `reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/source_state_matrix.json`
- `reports/agent_jobs/cockpit_source_drawer_semantics_audit_v1_20260526/validation.json`

## Validation

- Controller task-card validate/check-diff.
- Read-only backend metadata inspection.
- Read-only UI/static inspection.
- Existing focused test inspection and attempted local test execution.
- Duplicate issue search.
- `git diff --check`.
