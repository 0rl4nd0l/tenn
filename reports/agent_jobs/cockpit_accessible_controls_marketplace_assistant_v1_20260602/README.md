# Cockpit Accessible Controls: Marketplace Assistant

Status: ready for review

## Scope

This slice addresses one narrow part of GitHub issue #53:

- Marketplace assistant prompt textarea now has a durable accessible name.
- Focused Marketplace assistant tests query the prompt by role/name.
- The same focused test now uses the current visible button name, `Save and run now`, instead of the stale `Deploy + run now` assertion.

This does not close #53. The issue remains open for broader route-level accessibility coverage.

## Boundaries

No backend, retrieval, storage, parser, source-label, memory, financial truth, marketplace persistence, or runtime behavior was changed. The change is limited to the Marketplace assistant UI and focused component test.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_marketplace_assistant_v1_20260602.md`
- `./node_modules/.bin/vitest run components/cockpit/marketplace/marketplace-assistant.test.tsx`
- `./node_modules/.bin/eslint components/cockpit/marketplace/marketplace-assistant.tsx components/cockpit/marketplace/marketplace-assistant.test.tsx`
- `./node_modules/.bin/tsc --noEmit`
- `git diff --check`

The isolated worktree temporarily symlinked `cockpit-ui/node_modules` to the shared checkout's dependency directory for local validation because `pnpm` was not available on `PATH` and the sibling worktree had no local `node_modules`. The symlink was removed before staging.
