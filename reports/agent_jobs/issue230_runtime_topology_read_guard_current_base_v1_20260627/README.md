# Issue #230 Runtime Topology Read Guard

## Status

status: DONE_WITH_RISK

DONE_WITH_RISK: current-base backend/client fix implemented and backend
validation passed. Local frontend Vitest/ESLint validation is blocked because
this checkout does not have `vitest` or `eslint` installed in
`cockpit-ui/node_modules`. No live backend/Cockpit runtime smoke was started.

## Scope

- GitHub issue: #230
- Pull request: https://github.com/0rl4nd0l/tenn/pull/440
- Branch: `safe/issue230-runtime-topology-read-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- Task card: `docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md`
- Duplicate-work classification: `NO_MATCHING_ACTIVE_WORK_FOUND`

## Changes

- Added `Depends(require_api_key)` to backend runtime-topology reads:
  - `GET /api/cockpit/config`
  - `GET /api/cockpit/models`
  - `GET /api/cockpit/queue`
- Added focused backend tests for route dependency registration, missing/wrong
  key denial before runtime/model/queue probing, and matching-key success.
- Updated Cockpit API-client helpers and direct `/api/cockpit/config` browser
  fetches to send `X-API-Key` from localStorage or `NEXT_PUBLIC_API_KEY`.
- Updated backend API surface docs for the guarded route contract.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Cockpit runtime-topology reads deny unauthenticated configured-key requests before exposing config, models, or queue state. |
| live output location | `/api/cockpit/config`, `/api/cockpit/models`, `/api/cockpit/queue`. |
| pre-run max timestamp or count | RED focused backend pytest: 9 failed, 18 passed. |
| post-run max timestamp or count | GREEN focused backend pytest: 27 passed. Live service count/timestamp: DATA_MISSING. |
| rows/files inserted or updated after run start | Production rows: 0. Repo files changed are restricted to task-card allowlist. |
| readiness/gate status | Local backend tests pass; local frontend tests/lint blocked by missing `vitest`/`eslint`; PR/CI pending. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | No approved live runtime/API smoke; local frontend validation cannot run without installed Node test tools. |

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`,
  `docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md`,
  `docs/architecture/19_backend_api_surface.md`
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: none
- `reason`: backend runtime-topology read auth behavior changed.

## Unsafe Actions Avoided

- No DB, Qdrant, Redis, source document, report data, memory store, gold label,
  parser prompt, runtime service, model/GPU config, or production data mutation.
- No dependency install or lockfile/package manifest mutation.
- No merge, rebase, reset, stash, clean, branch deletion, or issue close.

## Next

PR #440 is open. Wait for CI, then close issue #230 only after the PR is merged
or owner explicitly approves issue closeout from PR evidence.
