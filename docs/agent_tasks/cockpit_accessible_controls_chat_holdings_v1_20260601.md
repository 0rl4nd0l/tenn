---
job_id: cockpit_accessible_controls_chat_holdings_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md
  - reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601/README.md
  - reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601/status.json
  - reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601/diff-check.json
  - reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601/accessibility_after.json
  - cockpit-ui/components/cockpit/chat/terminal-input.tsx
  - cockpit-ui/components/cockpit/chat/terminal-input.test.tsx
  - cockpit-ui/components/cockpit/holdings/holdings-screen.tsx
  - cockpit-ui/components/cockpit/holdings/holdings-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_accessible_controls_chat_holdings_v1_20260601
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Accessible Controls Chat And Holdings

Safe-extension task for issue #53.

## Lane

Primary lane: Reporting.

## Objective

Fix the lowest-collision accessible-name failures reproduced by the issue #53
audit for `/full-chat` and `/holdings`, without changing data behavior,
backend contracts, or layout intent.

## Scope

Allowed:

- Add a durable accessible name to the full-chat command input.
- Add durable accessible names to Holdings selects, create-holding inputs, and
  filter controls.
- Add focused tests proving the new accessible names are queryable.
- Create this task card and report artifacts.

Forbidden:

- Do not change backend/runtime/data/memory/extraction surfaces.
- Do not change canonical financial truth, parser routing, prompts, gold
  labels, model/runtime/GPU/service config, or production data.
- Do not touch Marketplace, History, Verification, Operations, Watchlist,
  Thesis Audit, Home, Boot, or other files owned by open adjacent PRs.
- Do not redesign the Holdings or chat UI.
- Do not remove visible placeholders; accessible names must be additive.

## Acceptance Criteria

- `/full-chat` command input has a programmatic accessible name.
- `/holdings` portfolio select, create-holding fields, search field, status
  filter, and sort filter have programmatic accessible names.
- Focused tests can find the remediated controls by accessible role/name.
- A rendered DOM audit for `/full-chat` and `/holdings` shows zero failures for
  this slice.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-input.test.tsx components/cockpit/holdings/holdings-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- Playwright Chromium DOM audit for `/full-chat` and `/holdings`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md`
- release the registry claim before final report
