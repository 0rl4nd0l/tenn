# Code Review WithApiKey Test Mock Follow-Up

Status: DONE_WITH_RISK

## Scope

This job fixes a code-review finding from the issue #230 current-base merge:
two Cockpit component tests mocked `@/lib/api-client` without exporting
`withApiKey`, while the components now import that helper.

## Files Changed

- `cockpit-ui/components/cockpit/chat/chat-screen.test.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx`
- `docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md`
- `reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/`

## Result

Both local API-client mocks now expose:

```ts
withApiKey: vi.fn(() => ({ 'X-API-Key': 'test-key' }))
```

This keeps the test module mock surface aligned with the guarded
runtime-topology route changes.

## Boundaries

- No product runtime, backend, extraction, data, prompt, model, service, DB,
  Qdrant, Redis, source PDF, package, or lockfile changes.
- No runtime functionality proof was required or attempted; this was a focused
  component-test mock repair.

## Runtime Functionality Proof

| Field | Evidence |
| --- | --- |
| intended output | Focused Cockpit component tests can load their mocked `@/lib/api-client` module after components import `withApiKey`. |
| live output location | `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-screen.test.tsx components/cockpit/cockpit-sidebar.test.tsx` |
| pre-run max timestamp or count | DATA_MISSING; no executable local Vitest baseline because `vitest` is unavailable in this worktree. |
| post-run max timestamp or count | DATA_MISSING; focused Vitest command could not execute. |
| rows/files inserted or updated after run start | 2 test files updated after run start; no data rows inserted or updated. |
| readiness/gate status | Static/containment gates passed; executable frontend test gate blocked locally by missing `vitest`. |
| exact command/query used | `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-screen.test.tsx components/cockpit/cockpit-sidebar.test.tsx` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Local frontend dependencies are not installed; `pnpm exec` reports `Command "vitest" not found`. |

result: DATA_MISSING
