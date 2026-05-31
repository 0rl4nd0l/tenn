---
job_id: cockpit_marketplace_empty_state_actionability_v1_20260526
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_marketplace_empty_state_actionability_v1_20260526.md
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/README.md
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/status.json
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/diff-check.json
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/marketplace-matches-empty-state.png
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/marketplace-alerts-empty-state.png
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/marketplace-matches-empty-state-mobile.png
  - reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526/marketplace-alerts-empty-state-mobile.png
  - cockpit-ui/components/cockpit/marketplace/matches-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/matches-screen.test.tsx
  - cockpit-ui/components/cockpit/marketplace/alerts-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/alerts-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_marketplace_empty_state_actionability_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Marketplace Empty State Actionability V1

Resolve GitHub issue #93 by making the Marketplace Matches and Alerts empty states explain the mission/run evidence behind the zero-result state and show a clear next action.

## Scope

- Load mission context only for zero-result Marketplace Matches and Alerts states.
- Distinguish no missions, missions without recorded scans, scans with zero results, active filters hiding results, and unavailable mission/run evidence.
- Preserve backend/API authority and show `DATA_MISSING` when context needed for the empty-state explanation cannot be loaded.
- Add focused regression coverage for zero-result states with and without mission context.

## Forbidden

- No production DB/Qdrant/news/memory writes.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No backend/runtime/model/GPU/service config changes.
- No fabricated matches, alerts, scans, or mission evidence.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_marketplace_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_marketplace_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_marketplace_empty_state_actionability_v1_20260526.md`
- focused Marketplace component tests
- targeted ESLint for changed files
- TypeScript
- Next build if practical
- desktop and mobile browser screenshots for `/marketplace/matches` and `/marketplace/alerts`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_marketplace_empty_state_actionability_v1_20260526.md`
