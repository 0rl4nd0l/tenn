# Cockpit Accessible Controls Chat And Holdings

## Summary

This safe-extension slice remediates the issue #53 accessible-name failures for
`/full-chat` and `/holdings`.

The change is additive only:

- the full-chat command input now has a durable accessible name;
- Holdings portfolio/filter select triggers now have durable accessible names;
- Holdings create/filter text inputs now have durable accessible names;
- focused tests prove the remediated controls are queryable by role/name.

No backend, data, memory, extraction, runtime, source-label, or financial-truth
surface was changed.

## Current Evidence

- Duplicate checks found issue #53 and no existing chat+holdings accessibility
  implementation PR.
- Registry overlap check passed before claiming the task.
- Rendered DOM audit after the patch checked `/full-chat` and `/holdings` with
  empty `DATA_MISSING`-shaped API responses.
- Post-patch inventory: 43 visible controls, 0 accessible-name failures, 0
  console errors, 0 page errors.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_chat_holdings_v1_20260601.md`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-input.test.tsx components/cockpit/holdings/holdings-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/chat/terminal-input.tsx components/cockpit/chat/terminal-input.test.tsx components/cockpit/holdings/holdings-screen.tsx components/cockpit/holdings/holdings-screen.test.tsx`
- Playwright Chromium DOM audit for `/full-chat` and `/holdings`

## Artifacts

- `accessibility_after.json`: rendered DOM inventory after remediation.
- `validation.json`: task-card validation.
- `status.json`: registry claim/release status.
- `diff-check.json`: task-card diff validation.
