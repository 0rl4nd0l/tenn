---
job_id: cockpit_accessible_controls_marketplace_assistant_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_accessible_controls_marketplace_assistant_v1_20260602
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md
  - cockpit-ui/components/cockpit/marketplace/marketplace-assistant.tsx
  - cockpit-ui/components/cockpit/marketplace/marketplace-assistant.test.tsx
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_assistant_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_assistant_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_assistant_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_assistant_v1_20260602/diff-check.json
github_comment_targets:
  - 53
---

# Task

Implement a narrow #53 accessible-control remediation slice for the Marketplace assistant prompt only.

# Scope

- Add a durable accessible name to the Marketplace assistant prompt textarea.
- Update focused component tests to query the textarea by role/name.
- Keep #53 open because this is only one Marketplace sub-surface.

# Boundaries

- Do not edit Marketplace mission, matches, alerts, match detail, backend, runtime, data, parser, prompt, memory, source, gold-label, model, GPU, or service-config files.
- Do not change request payloads, backend API routes, retrieval behavior, canonical financial truth, DB, Qdrant, marketplace persistence, or memory stores.
- Do not redesign the Marketplace assistant.
- Do not close #53.

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- focused Vitest for `marketplace-assistant.test.tsx`
- targeted ESLint for touched Marketplace assistant files
- TypeScript check for Cockpit UI
- JSON parse checks for report artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_registry.py release cockpit_accessible_controls_marketplace_assistant_v1_20260602`

# Definition Of Done

- Marketplace assistant prompt is discoverable by role/name.
- Existing Marketplace assistant behavior remains unchanged.
- #53 receives a status comment linking the PR and noting that broader route coverage remains open.
- No forbidden surfaces are changed.
