---
job_id: cockpit_watchlist_empty_state_actionability_v1_20260526
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/README.md
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/status.json
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/diff-check.json
  - reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/watchlist-empty-state.png
  - cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx
  - cockpit-ui/components/cockpit/watchlist/watchlist-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Watchlist Empty State Actionability V1

Resolve GitHub issue #92 by making the empty Watchlist surface use source-grounded holdings context when available, and explicit `DATA_MISSING` copy when no candidate source is available.

## Scope

- Load existing `/api/cockpit/holdings` context for empty Watchlist suggestions.
- Show source-grounded current-holding ticker candidates while preserving the manual add flow.
- Let users add a suggested ticker without retyping it.
- Keep duplicate/add failures visible.
- Add focused regression tests for empty watchlist plus holdings-derived candidates and no-candidate `DATA_MISSING`.

## Forbidden

- No production DB/Qdrant/news/memory writes outside the existing user-triggered watchlist add endpoint.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No backend/runtime/model/GPU/service config changes.
- No synthetic recommendations without visible source context.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- focused Watchlist component tests
- targeted ESLint for changed files
- TypeScript
- Next build if practical
- browser screenshot for `/watchlist`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
