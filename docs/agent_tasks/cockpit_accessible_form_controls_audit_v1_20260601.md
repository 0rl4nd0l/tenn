---
job_id: cockpit_accessible_form_controls_audit_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/README.md
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/status.json
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/diff-check.json
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/accessibility_inventory.json
  - reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601/findings.md
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260601
mutation_mode: audit_only
production_data_access: false
---

# Cockpit Accessible Form Controls Audit

Audit-only task for issue #53.

## Lane

Primary lane: Reporting.

## Objective

Reproduce the current Cockpit route-by-route accessible-name inventory for
visible form controls and icon-only controls, then identify the smallest safe
follow-up remediation slice.

## Scope

Allowed:

- Create this task card and report artifacts.
- Run read-only static, DOM, or accessibility inspections against Cockpit UI
  routes.
- Record `DATA_MISSING` where a route cannot be rendered or current evidence
  cannot be collected.
- Recommend later focused implementation tasks with exact files and validation
  commands.

Forbidden:

- Do not modify product source files in this task.
- Do not change backend/runtime/data/memory/extraction surfaces.
- Do not change canonical financial truth, parser routing, prompts, gold
  labels, model/runtime/GPU/service config, or production data.
- Do not touch files owned by active or open adjacent Cockpit UI PRs.
- Do not rely on the missing `/tmp/tenn-ui-production-deep-audit.json`
  artifact as current proof.

## Acceptance Criteria

- Current GitHub duplicate/PR overlap checks are recorded.
- Current route evidence is produced for affected Cockpit routes or explicitly
  marked `DATA_MISSING`.
- The audit distinguishes visible text from programmatic accessible names.
- Any follow-up implementation slice lists exact files and focused validation.
- No product files are changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md`
- Route-by-route DOM/accessibility audit where the app can render locally.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md`
- release the registry claim before final report
