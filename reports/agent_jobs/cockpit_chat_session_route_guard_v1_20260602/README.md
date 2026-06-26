# Cockpit Chat Session Route Guard

Status: `DONE_WITH_RISK`

Issue: #229

Draft PR: #445
https://github.com/0rl4nd0l/tenn/pull/445

Worktree:
`/home/l4nd0/tenn-issue229-cockpit-chat-session-route-guard-current-base-v1-20260627`

Branch:
`safe/issue229-cockpit-chat-session-route-guard-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
at `7d6ab6c184332d5413700eb08e6790f530000942`

## Summary

This lane guards the direct backend Cockpit chat/session routes with the
existing configured local API-key dependency and forwards the configured browser
API key through the normal Cockpit chat/session client path.

Changed:

- `GET /api/cockpit/chat/sessions`
- `POST /api/cockpit/chat/sessions`
- `GET /api/cockpit/chat/sessions/{session_id}`
- `DELETE /api/cockpit/chat/sessions/{session_id}`
- `POST /api/cockpit/chat`
- Cockpit browser client calls for session CRUD, blocking chat, and SSE chat

Not changed:

- Attachment upload routes.
- Legacy chat route ownership.
- Action-control routes.
- Router-wide Cockpit auth.
- Chat evidence, persistence, source-label, prompt, runtime, DB, or service
  semantics.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Direct chat/session routes deny missing/wrong API keys when configured, and authenticated local calls still execute. |
| live output location | Local FastAPI `TestClient` routes under `/api/cockpit/chat*`; frontend header path in `cockpit-ui/lib/api-client.ts`. |
| pre-run max timestamp or count | `DATA_MISSING`; no live deployed backend or browser runtime was probed. |
| post-run max timestamp or count | `DATA_MISSING`; no live deployed backend or browser runtime was probed. |
| rows/files inserted or updated after run start | Backend tests prove rejected requests insert/delete zero session rows; source/report files changed in git worktree only. |
| readiness/gate status | Backend focused tests green; local frontend Vitest blocked because `node_modules/.bin/vitest` is absent. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | Local frontend Vitest was not runnable without dependency installation approval; no live browser/runtime route probe was performed. |

result: PARTIAL

## Closeout

The root backend auth gap is fixed and locally tested. The frontend forwarding
code and test coverage were added, but the local frontend test runner is absent
in this checkout. Use `Refs #229` until CI or an approved dependency install
validates the frontend test.
