---
job_id: cockpit_global_chrome_operator_detail_gate_v1_20260526
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/README.md
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/status.json
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/diff-check.json
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/home.png
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/full-chat.png
  - reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/operations.png
  - cockpit-ui/components/cockpit/cockpit-sidebar.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
  - cockpit-ui/components/cockpit/cockpit-status-bar.tsx
  - cockpit-ui/components/cockpit/cockpit-status-bar.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Global Chrome Operator Detail Gate V1

Resolve GitHub issue #109 by keeping raw host, GPU, and runtime/config internals out of normal analyst-facing global Cockpit chrome while preserving honest availability states and explicit operator detail affordances.

## Scope

- Replace sidebar host/GPU raw summaries with concise user-readable telemetry state.
- Replace sidebar raw Cockpit Config internals with a user-safe runtime/config readiness summary and an explicit Settings path for operator detail.
- Remove raw model IDs, max-token, temperature, routing-policy, and profile badges from the global status bar.
- Add focused component coverage proving raw command/config text is not rendered in normal chrome.
- Preserve Host/GPU detail dialogs and Settings as explicit operator/debug affordances.

## Forbidden

- No backend route, runtime probe, GPU command, runtime/model/GPU/service config, parser, extraction, canonical financial truth, DB/Postgres, Qdrant, news, or memory changes.
- No mutation of production data.
- No route/user intent alias storage in thesis or memory surfaces.
- No unrelated dirty work, cleanup, reset, stash, or broad formatting.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md`
- focused Vitest for sidebar/status-bar tests
- targeted ESLint for changed UI/test files
- TypeScript
- Next build
- Playwright screenshots for Home, Full Chat, and Operations if practical
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md`
