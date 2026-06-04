# Cockpit Chat Operator Diagnostics Visibility Gate

Issue: #108

Branch: `safe/cockpit-chat-operator-diagnostics-gate-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-chat-operator-diagnostics-gate-v1-20260602`

## Outcome

Implemented a UI-only normal-chat visibility gate for issue #108. Normal
Cockpit chat diagnostic handoffs now render a user-safe message that says a
potential issue was captured for operator review and preserves `DATA_MISSING`
honesty, without report IDs, report paths, diagnostic API links, draft repair
prompt paths, investigation packet paths, copied-prompt status, or Codex deploy
metadata.

Operator diagnostics remain available only when the explicit frontend flag
`NEXT_PUBLIC_COCKPIT_OPERATOR_DIAGNOSTICS=1` is set. In that mode the existing
operator handoff text and deploy metadata are preserved.

## Boundaries

- No backend, query orchestration, retrieval, memory, Qdrant/Postgres,
  financial truth, source/evidence label, runtime/model/GPU, diagnostic route,
  or service config changes.
- No changes to diagnostic persistence or Codex deployment execution.
- Operator diagnostics must remain available only behind an explicit operator
  mode.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the lockfile.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-operator-diagnostics.test.ts components/cockpit/chat/terminal-message.test.tsx` passed: 2 files, 17 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/chat/chat-screen.tsx components/cockpit/chat/chat-operator-diagnostics.ts components/cockpit/chat/chat-operator-diagnostics.test.ts` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.
- `NEXT_PUBLIC_COCKPIT_OPERATOR_DIAGNOSTICS=0 corepack pnpm --dir cockpit-ui exec next dev --hostname 127.0.0.1 --port 3026` served the PR worktree for browser validation.
- `COCKPIT_E2E_BASE_URL=http://127.0.0.1:3026 COCKPIT_ROUTE_PARITY_REPORT_PATH=/tmp/cockpit_chat_operator_diagnostics_browser_regression_20260602.md corepack pnpm --dir cockpit-ui exec playwright test tests/chat-browser-regression.spec.ts --project=chromium --retries=0` passed: 4 tests, including `/full-chat` mocked `auto_flag` and manual flag flows in normal mode.
- `python3 -m json.tool` passed for the report JSON files.
- Code-reviewer pass found no blocking findings.
- `git diff --check && git diff --cached --check` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_operator_diagnostics_gate_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py release cockpit_chat_operator_diagnostics_gate_v1_20260602` passed.
- Final `python3 scripts/agent_job_registry.py list-active` passed with no active jobs.

## Remaining Caveat

- The browser proof uses deterministic Playwright route mocks for the SSE
  `auto_flag` and feedback capture payloads. It proves `/full-chat` rendering
  behavior for normal users without mutating backend diagnostics.
- A live model/backend path that independently decides to emit an auto-diagnostic
  was not forced in this UI slice and is not required for the rendering fix.
