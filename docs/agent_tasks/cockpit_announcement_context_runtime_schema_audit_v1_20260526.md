---
job_id: cockpit_announcement_context_runtime_schema_audit_v1_20260526
lane: Provenance
supporting_lanes:
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_announcement_context_runtime_schema_audit_v1_20260526.md
  - reports/agent_jobs/cockpit_announcement_context_runtime_schema_audit_v1_20260526/README.md
  - reports/agent_jobs/cockpit_announcement_context_runtime_schema_audit_v1_20260526/status.json
  - reports/agent_jobs/cockpit_announcement_context_runtime_schema_audit_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_announcement_context_runtime_schema_audit_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_announcement_context_runtime_schema_audit_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 84
---

# Cockpit Announcement Context Runtime Schema Audit

## Objective

Classify the `cockpit_announcement_context` runtime schema expectation for
issue #84 without mutating schema, data, provenance labels, query routing, or
answer-source behavior.

## Scope

This is a report-only audit. It may inspect repo code, tests, task cards,
GitHub issue/PR state, and current read-only runtime availability. It must not
create migrations, run migrations, materialize tables, modify database rows, or
weaken missing-evidence handling.

## Contract Safety

- Target layer: Provenance and Retrieval/Analysis boundary evidence only.
- Relevant contract: backend remains the authority for context/provenance data;
  Cockpit must not create alternate data authority or relabel missing evidence.
- Must not change: backend schema, DB/Qdrant/news/memory stores, source-label
  semantics, financial truth, extraction, parser routing, prompt behavior, or
  runtime/service config.
- Runtime evidence: read-only inspection only. No production data access.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_announcement_context_runtime_schema_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_announcement_context_runtime_schema_audit_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_announcement_context_runtime_schema_audit_v1_20260526.md --repo-root .`
- repo search for `cockpit_announcement_context`
- Alembic migration search for table ownership
- duplicate issue/PR search
- JSON validation
- path-redaction scan
- `git diff --check`
- task-card `check-diff`
- registry release before final report

## Hard Stops

- Any schema migration, table creation, table population, or runtime DB write.
- Any change to contested query/provenance/Cockpit route surfaces.
- Any fix that hides missing evidence or labels absent announcement context as
  source-backed.
- Active same-file collision with another task card.
