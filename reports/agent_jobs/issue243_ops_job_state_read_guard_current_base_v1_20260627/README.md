# Issue #243 Ops Job-State Read Guard

## Status

status: DONE_WITH_RISK

DONE_WITH_RISK: current-base fix implemented and backend validation passed.
Frontend Ops client and ESLint validation are blocked locally because
`cockpit-ui/node_modules`, `cockpit-ui/node_modules/.bin/vitest`, and
`cockpit-ui/node_modules/.bin/eslint` are absent. No runtime service or live API
smoke was started.

## Scope

- GitHub issue: #243
- Pull request: https://github.com/0rl4nd0l/tenn/pull/437
- Branch: `safe/issue243-ops-job-state-read-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- Task card: `docs/agent_tasks/issue243_ops_job_state_read_guard_current_base_v1_20260627.md`
- Old work classification: `ADOPT/PRESERVE`

## Changes

- Added `Depends(require_api_key)` to Ops job-state read routes and the Ops SSE
  stream.
- Added focused backend guard tests for dependency registration and configured
  key denial/success.
- Updated Cockpit Ops job-state reads to send `X-API-Key` when configured.
- Replaced native `EventSource` usage with header-capable `sse.js` stream
  construction using `start: false`.
- Added focused Ops API-client tests for read headers and stream header
  construction.
- Updated backend API surface docs for the `/api/ops/*` auth contract.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Ops job-state read routes and SSE stream deny configured-key unauthenticated calls and allow authenticated operator reads/streams. |
| live output location | `/api/ops/jobs`, `/jobs/active`, `/jobs/{job_id}`, `/jobs/{job_id}/events`, `/jobs/{job_id}/artifacts`, `/stream`. |
| pre-run max timestamp or count | RED focused pytest: 8 expected failures and 23 passes. |
| post-run max timestamp or count | GREEN focused backend suite: 31 passed. Live service count/timestamp: DATA_MISSING. |
| rows/files inserted or updated after run start | Production rows: 0. Repo files changed are restricted to task-card allowlist. |
| readiness/gate status | Local backend tests pass; frontend Vitest/ESLint blocked by missing local dependencies; PR/CI pending. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | Local frontend dependencies absent; no approved live runtime/API smoke. |

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, `docs/architecture/19_backend_api_surface.md`
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: none
- `reason`: route auth behavior changed for Ops job-state read and stream APIs.

## Unsafe Actions Avoided

- No DB, Qdrant, Redis, source document, report data, memory store, gold label,
  parser prompt, runtime service, model/GPU config, or production data mutation.
- No dependency install or lockfile/package manifest mutation.
- No merge, rebase, reset, stash, clean, branch deletion, or issue close.

## Next

PR #437 is open. Wait for CI, then close issue #243 only after the PR is merged
or owner explicitly approves issue closeout from PR evidence.
