# Issue #242 Context Diagnostics Guard

## Status

status: DONE_WITH_RISK

DONE_WITH_RISK: current-base source fix implemented and backend validation
passed. Frontend Vitest/ESLint validation is blocked locally because
`cockpit-ui/node_modules`, `cockpit-ui/node_modules/.bin/vitest`, and
`cockpit-ui/node_modules/.bin/eslint` are absent. No live backend/Cockpit
runtime smoke was started.

## Scope

- GitHub issue: #242
- Pull request: https://github.com/0rl4nd0l/tenn/pull/438
- Branch: `safe/issue242-context-diagnostics-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- Task card: `docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md`
- Old work classification: `ADOPT/PRESERVE`

## Changes

- Added configured-key diagnostic redaction for unauthenticated
  `GET /api/context/ticker`.
- Preserved the full ticker diagnostic payload for authenticated requests and
  no-key local-dev mode.
- Required `require_api_key` on `GET /api/context/verification` and
  `GET /api/context/verification/runs`.
- Updated Cockpit context and verification-run clients to send `X-API-Key`.
- Replaced the verification screen's direct `fetch()` for run history with the
  API-client helper.
- Added focused backend tests for redaction, route guards, authenticated access,
  and no-key local-dev behavior.
- Added focused frontend API-client tests for context diagnostic header
  propagation.
- Updated backend API surface docs for the context diagnostics auth/redaction
  contract.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Context diagnostic fields are redacted from unauthenticated configured-key ticker reads, and verification diagnostic reads require `X-API-Key`. |
| live output location | `/api/context/ticker`, `/api/context/verification`, `/api/context/verification/runs`. |
| pre-run max timestamp or count | RED focused pytest: 5 failed, 2 passed. |
| post-run max timestamp or count | GREEN focused backend pytest: 7 passed. Live service count/timestamp: DATA_MISSING. |
| rows/files inserted or updated after run start | Production rows: 0. Repo files changed are restricted to task-card allowlist. |
| readiness/gate status | Local backend tests pass; frontend Vitest/ESLint blocked by missing local dependencies; PR/CI pending. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | Local frontend dependencies absent; no approved live runtime/API smoke. |

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, `docs/architecture/SYSTEM_CONTRACT.md`, `docs/architecture/19_backend_api_surface.md`
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: none
- `reason`: context diagnostics auth/redaction behavior changed.

## Unsafe Actions Avoided

- No DB, Qdrant, Redis, source document, report data, memory store, gold label,
  parser prompt, runtime service, model/GPU config, or production data mutation.
- No dependency install or lockfile/package manifest mutation.
- No merge, rebase, reset, stash, clean, branch deletion, or issue close.

## Next

PR #438 is open. Wait for CI, then close issue #242 only after the PR is merged
or owner explicitly approves issue closeout from PR evidence.
