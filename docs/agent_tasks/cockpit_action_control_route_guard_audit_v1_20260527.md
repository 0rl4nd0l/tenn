---
job_id: cockpit_action_control_route_guard_audit_v1_20260527
title: Cockpit action-control route guard audit
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Repo Hygiene
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527
allowed_files:
  - docs/agent_tasks/cockpit_action_control_route_guard_audit_v1_20260527.md
  - reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/README.md
  - reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/route_guard_matrix.json
  - reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/status.json
  - reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/validation.json
  - reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/diff-check.json
---

# Cockpit Action-Control Route Guard Audit

## Objective

Resolve the audit deliverable for GitHub issue #121 by inventorying broader
Cockpit action/control routes and classifying current server-side guard parity
without executing live actions or editing contested route files.

## Allowed Read-Only Surfaces

- Backend Cockpit action/control route source.
- Next.js Cockpit BFF route source.
- Focused route/test files for evidence only.
- Task card and report artifacts.

## Forbidden

- No live action execution, stopping, restarting, scanning, calibration, sync,
  benchmark refresh, marketplace mutation, model load, or runtime probe that can
  mutate state.
- No backend route edits, frontend BFF edits, broad auth redesign, or guard
  implementation in this audit.
- No DB, Qdrant, news, memory, canonical financial truth, parser routing,
  extraction prompt, gold label, model/runtime/GPU/service config, branch
  cleanup, reset, stash, or delete mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_action_control_route_guard_audit_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_action_control_route_guard_audit_v1_20260527.md`
- Claim and release the task card.
- JSON validation for generated route matrix and status artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_action_control_route_guard_audit_v1_20260527.md`

## Done Criteria

- The report identifies action/control routes exposed through the backend and
  BFF surfaces reviewed in this pass.
- Each route is classified as guarded, unguarded, read-only, or DATA_MISSING
  with line-level evidence.
- Unsafe mutation-capable routes are linked to a separate safe-extension
  implementation recommendation instead of being edited here.
- No forbidden mutation occurred.
