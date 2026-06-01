# Chat Pending Action State Audit

Generated: 2026-06-02T02:35:47+10:00

## Scope

- GitHub issue: #120, `[Query Orchestration] Pending action proposal can block the next normal chat prompt`
- Lane: Query Orchestration
- Mode: SAFE EXTENSION
- Worktree: `/home/l4nd0/tenn-chat-pending-action-normal-followup-v1-20260602`
- Branch: `safe/chat-pending-action-normal-followup-v1-20260602`

## Finding

Current `ChatScreen.handleSend()` already treats a non-confirm/non-cancel message as an independent chat turn while an action proposal is pending. The regression gap was missing focused coverage for the Gemini audit sequence.

## Change

Added a focused Chromium Playwright regression that:

- opens `/full-chat`
- receives an `action_preview` SSE event
- verifies `Confirm` and `Cancel` are visible
- submits a normal follow-up prompt: `Pick one current holding or watchlist item for review.`
- verifies an independent answer renders
- verifies `actionJobPostCount` remains `0`
- cancels the proposal intentionally and verifies no action job was posted

No backend, data, memory, retrieval, financial-truth, runtime, model, GPU, parser, prompt, or gold-label files were changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md` PASS
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md` PASS
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_pending_action_state_audit_v1_20260526.md` PASS
- `PLAYWRIGHT_BASE_URL=http://localhost:3000 COCKPIT_ROUTE_PARITY_REPORT_PATH=reports/agent_jobs/chat_pending_action_state_audit_v1_20260526/browser_regression_route_parity.md corepack pnpm exec playwright test tests/chat-browser-regression.spec.ts --project=chromium -g "normal follow-up is independent"` PASS
- `corepack pnpm exec eslint tests/chat-browser-regression.spec.ts` PASS
- `git diff --check` PASS

## Notes

An attempted full-file Chromium run exposed an unrelated legacy assertion failure for the unsupported-claim label. That failure occurs after the #120 path and is not changed here. The focused #120 regression passed against `http://localhost:3000`; Next dev blocked the `127.0.0.1` HMR origin in this local validation environment.
