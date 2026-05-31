---
job_id: news_empty_state_value_audit_v1_20260526
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
owner: Codex
mutation_mode: audit_only
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_empty_state_value_audit_v1_20260526
production_data_access: false
allow_audit_code_changes: false
github_mutation_allowed: false
issue_number: 116
allowed_files:
  - docs/agent_tasks/news_empty_state_value_audit_v1_20260526.md
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/**
allowed_repo_files:
  - docs/agent_tasks/news_empty_state_value_audit_v1_20260526.md
  - reports/agent_jobs/news_empty_state_value_audit_v1_20260526/**
forbidden:
  - product/backend/frontend/runtime code changes
  - production DB/Qdrant/news/memory
  - canonical financial truth
  - parser routing
  - extraction prompts
  - gold labels
  - runtime/model/GPU/service config
  - unsourced proactive news summaries
  - unrelated dirty work
---

# News Empty-State Value Audit

## Objective

Audit the first-use `/news` workflow and adjacent Home/chat handoff evidence to
decide whether a News empty-state remediation issue is warranted.

## Required Outputs

- `reports/agent_jobs/news_empty_state_value_audit_v1_20260526/README.md`
- `reports/agent_jobs/news_empty_state_value_audit_v1_20260526/status.json`
- `reports/agent_jobs/news_empty_state_value_audit_v1_20260526/workflow_matrix.json`
- `reports/agent_jobs/news_empty_state_value_audit_v1_20260526/validation.json`

## Validation

- Controller task-card validate/check-diff.
- Read-only source/static inspection.
- Existing browser-audit artifact inspection.
- Duplicate issue search.
- `git diff --check`.
