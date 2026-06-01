---
job_id: home_data_missing_jam_triage_v1_20260526
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/home_data_missing_jam_triage_v1_20260526.md
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/README.md
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/status.json
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/jam_evidence.json
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/gap_mapping.json
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/runtime_probe.json
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/validation.json
  - reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/home_data_missing_jam_triage_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 41
---

# Home Data Missing Jam Triage

## Objective

Refresh and preserve the #41 Home `DATA_MISSING` Jam evidence, then map each
visible Home gap to an existing tracker, `DATA_MISSING`, or a bounded follow-up
recommendation without changing product code.

## Scope

This task is audit-only. It may inspect the linked Jam, issue text, duplicate
space, adjacent issue/PR links, current local service availability, and
read-only localhost responses if services are already running.

## Contract Safety

- Target layer: Client/Reporting audit only.
- Relevant contract: Cockpit remains a client/orchestration layer; backend
  remains the source of authoritative data and retrieval.
- Must not change: retrieval behavior, evidence labels, Home data synthesis,
  DB, Qdrant, news stores, memory stores, financial truth, parser routing,
  extraction prompts, gold labels, model/runtime/GPU/service config.
- GPU process check: not required; this audit does not spawn, restart, or
  depend on llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/home_data_missing_jam_triage_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/home_data_missing_jam_triage_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/home_data_missing_jam_triage_v1_20260526.md --repo-root .`
- Jam metadata/screenshot/console/network/user-event retrieval attempt.
- Current localhost 3000/8000 availability probe.
- Adjacent issue/PR mapping for #83, #86, #114, #116, #151, #159, and #179.
- JSON validation.
- Path-redaction scan.
- `git diff --check`.
- task-card `check-diff`.
- registry release before final report.

## Hard Stops

- Jam evidence cannot isolate a single root cause.
- Current services are not already running for a safe read-only reproduction.
- Any implementation would need product/runtime files without a proven route.
- Any fix would fabricate Home data or weaken DATA_MISSING/source labels.
