---
job_id: cockpit_home_actionability_helper_v1_20260522
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_actionability_helper_v1_20260522.md
  - reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/
  - reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/README.md
  - reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/status.json
  - reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/validation.json
  - reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/diff-check.json
  - cockpit-ui/lib/cockpit-home-actionability.ts
  - cockpit-ui/lib/cockpit-home-actionability.test.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/components/cockpit/home/**
  - cockpit-ui/components/cockpit/home/cards/attention-queue-card.tsx
  - cockpit-ui/components/cockpit/home/contextual-assistant.tsx
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/source-detail-drawer.tsx
  - cockpit-ui/tests/smoke.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Home Actionability Helper V1

Centralize Cockpit Home UI actionability rules and apply them across relevant Home surfaces without changing backend, runtime, truth, memory, parser, data store, route, or provider behavior.

## Scope

- Add a small UI-only helper under `cockpit-ui/lib/cockpit-home-actionability.ts`.
- Cover the helper with focused tests.
- Apply the helper to Cockpit Home surfaces that currently decide clickable, readonly, blocked, demo, degraded, `DATA_MISSING`, or source-handoff state locally.
- Preserve `DATA_MISSING`, degraded, demo-only, source label, and resolvable-source honesty.
- Carry forward smoke reliability hardening for sidebar navigation selectors.

## Required Behavior

- Source-backed actions remain enabled only when backend evidence is resolvable, non-demo, not degraded, and not blocked by source/handoff rules.
- Demo and mock states remain explicitly marked as not source-backed.
- `DATA_MISSING`, degraded, no-hit, operational trace, unknown, and missing source identity states must not be presented as verified or source-backed action.
- Home assistant empty-state copy must reflect current Home mode/status instead of implying live source-backed monitoring when Home is missing or degraded.
- Full Chat remains draft-only unless a resolvable Home source is attached.

## Forbidden

- No backend route invention or backend edits.
- No financial truth, canonical data, DB/Postgres, Qdrant, news store, memory store, extraction/parser, Appendix, runtime/model/GPU/provider, dependency, lockfile, Strategy Lab, Marketplace, Thesis Audit, or broad lint changes.
- No cleanup, deletion, moving, or staging of unrelated task-card artifacts in the shared worktree.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_actionability_helper_v1_20260522.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_actionability_helper_v1_20260522.md`
- `git diff --check`
- targeted ESLint for changed UI/test files
- focused Vitest for `cockpit-home-actionability`, `cockpit-home-api`, and existing Home contract/live-shape tests
- focused Chromium Playwright smoke for Home/sidebar navigation, if practical
- TypeScript
- Next build if practical
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_actionability_helper_v1_20260522.md`
