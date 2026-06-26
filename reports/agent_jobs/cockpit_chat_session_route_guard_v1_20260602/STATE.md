# State

`VERIFIED` current base:

- Worktree: `/home/l4nd0/tenn-issue229-cockpit-chat-session-route-guard-current-base-v1-20260627`
- Branch: `safe/issue229-cockpit-chat-session-route-guard-current-base-v1-20260627`
- HEAD before implementation: `7d6ab6c184332d5413700eb08e6790f530000942`
- Task card: `docs/agent_tasks/cockpit_chat_session_route_guard_v1_20260602.md`
- Registry job: `cockpit_chat_session_route_guard_v1_20260602`
- Draft PR: #445, https://github.com/0rl4nd0l/tenn/pull/445

`VERIFIED` duplicate/collision checks:

- Guard preflight returned `final_decision=pass`.
- Guard preflight returned `duplicate_work_classification=NO_MATCHING_ACTIVE_WORK_FOUND`.
- Registry `check-overlap` returned no active jobs.
- Ledger search for issue #229 returned no matches before implementation.

`VERIFIED` implementation:

- Backend chat/session routes now use `Depends(require_api_key)`.
- Rejected direct calls do not list/create/read/delete chat sessions.
- Rejected direct chat calls do not call `chat_stream`, finalization, auto
  flagging, or session-row mutation in focused tests.
- Configured-key direct calls preserve session CRUD, blocking chat, and SSE
  streaming behavior in focused tests.
- `cockpit-ui/lib/api-client.ts` now passes `X-API-Key` for chat/session CRUD,
  blocking chat, and SSE chat when `NEXT_PUBLIC_API_KEY` is configured.

`DATA_MISSING`:

- Local frontend Vitest execution. `npm test -- --run lib/api-client.test.ts`
  exited 127 because `vitest` was not installed in `cockpit-ui/node_modules`.
- Live deployed backend/browser functionality. No service was started and no
  runtime state was mutated.

Registry state:

- Released after PR #445 opened.
