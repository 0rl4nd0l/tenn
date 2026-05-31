# Cockpit Global Chrome Operator Detail Gate V1

## Result

Resolved GitHub issue #109 by removing raw host, GPU, and runtime/config internals from normal Cockpit sidebar and footer chrome.

## Scope

- Replaced visible sidebar host/GPU detail strings with concise telemetry summaries.
- Replaced the visible sidebar Cockpit Config internals block with `Runtime Readiness`, config status, and an explicit Settings link.
- Replaced footer model/token/temperature/source/profile badges with runtime and cloud-route readiness summaries.
- Sanitized backend/config warning text in global chrome so raw command output is not displayed.
- Added component tests covering sidebar and status-bar raw-detail suppression.

## Safety

- Target system layer: Client.
- Preserved backend authority, runtime probes, GPU commands, config endpoints, RAG, financial truth, memory, extraction, source labels, and storage behavior.
- Detailed Host/GPU diagnostics remain available through their explicit detail dialogs.
- Config/operator detail remains reachable through Settings.

## Visual Evidence

- `reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/home.png`
- `reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/full-chat.png`
- `reports/agent_jobs/cockpit_global_chrome_operator_detail_gate_v1_20260526/operations.png`

The screenshot run used `next start` on `127.0.0.1:3110` without starting the backend, so the captured UI shows backend-offline state. That is intentional for this UI-only chrome validation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md` - passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md` - passed
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md` - passed
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` - passed
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/cockpit-sidebar.test.tsx components/cockpit/cockpit-status-bar.test.tsx` - passed, 4 tests
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-sidebar.test.tsx components/cockpit/cockpit-status-bar.tsx components/cockpit/cockpit-status-bar.test.tsx` - passed
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit` - passed
- `corepack pnpm --dir cockpit-ui build` - passed
- Playwright CLI screenshots for Home, Full Chat, and Operations - passed with backend-offline console errors expected
- `git diff --check` - passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_global_chrome_operator_detail_gate_v1_20260526.md` - passed
