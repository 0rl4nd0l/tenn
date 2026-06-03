# Cockpit Source Parity And Suggested Actions

## Summary

Completed a bounded frontend slice for `#288` and `#122` on branch
`safe/cockpit-source-parity-suggested-actions-v1-20260603`.

- added a route-surface guard that verifies representative Cockpit source files
  exist and that core `/api/cockpit/*` frontend routes are covered by either a
  local route handler or the global `/api/:path*` rewrite, with matching backend
  FastAPI decorators
- wired `Pull market data` and `Run metric extraction` suggested-next actions
  into the existing preview -> confirm -> action-job progress flow
- kept `Review filing group` as a safe local UI action via the existing source
  drawer
- added focused tests for the new route guard, the button wiring, and the
  chat-screen preview/progress path

## Validation

- `node cockpit-ui/scripts/check-route-surface.mjs`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/route-surface.test.ts lib/cockpit-chat-actionability.test.ts components/cockpit/chat/terminal-message.test.tsx components/cockpit/chat/chat-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/chat/terminal-message.tsx components/cockpit/chat/chat-screen.tsx components/cockpit/chat/chat-screen.test.tsx lib/cockpit-chat-actionability.ts lib/cockpit-chat-actionability.test.ts lib/route-surface.test.ts scripts/check-route-surface.mjs`
- `corepack pnpm --dir cockpit-ui exec tsc -p tsconfig.json --noEmit --incremental false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`

## Notes

- `#120` was not widened into a separate remediation slice here. The new
  suggested-action path reuses the existing pending-action state and passed the
  focused chat-screen flow added in this work.
