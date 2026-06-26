# Issue #235 Memory Read Route Guard

## Status

status: DONE_WITH_RISK

DONE_WITH_RISK: current-base backend fix implemented and validation passed. No
live backend/Cockpit runtime smoke was started, and no production memory store
was read or mutated.

## Scope

- GitHub issue: #235
- Pull request: https://github.com/0rl4nd0l/tenn/pull/439
- Branch: `safe/issue235-memory-read-route-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- Task card: `docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md`
- Duplicate-work classification: `NO_MATCHING_ACTIVE_WORK_FOUND`

## Changes

- Added `Depends(require_api_key)` to backend memory read routes:
  - `GET /api/context/memory`
  - `GET /api/context/memory/index`
  - `GET /api/context/thesis`
  - `GET /api/context/company_dump`
- Added focused route-auth tests for dependency registration, missing/wrong key
  denial before memory work, matching-key success, and no-key local-dev
  behavior.
- Updated backend API surface docs for the memory-read auth contract.

Verified but not changed:

- Cockpit memory BFF routes already forward browser headers with
  `copyRequestHeaders(request)`.
- Memory Workbench browser reads already include `X-API-Key` when an `apiKey`
  prop is configured.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Backend memory read routes deny unauthenticated configured-key requests before durable memory payloads are loaded. |
| live output location | `/api/context/memory`, `/api/context/memory/index`, `/api/context/thesis`, `/api/context/company_dump`. |
| pre-run max timestamp or count | RED focused pytest: 9 failed, 8 passed. |
| post-run max timestamp or count | GREEN focused backend pytest: 17 passed; broader context endpoint suite: 36 passed. Live service count/timestamp: DATA_MISSING. |
| rows/files inserted or updated after run start | Production rows: 0. Repo files changed are restricted to task-card allowlist. |
| readiness/gate status | Local backend tests pass; PR/CI pending. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | No approved live runtime/API smoke. |

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, `docs/architecture/22_memory_ownership_map.md`, `docs/architecture/21_cockpit_client_contract.md`, `docs/architecture/19_backend_api_surface.md`
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: none
- `reason`: backend memory read auth behavior changed.

## Unsafe Actions Avoided

- No DB, Qdrant, Redis, source document, report data, memory store, gold label,
  parser prompt, runtime service, model/GPU config, or production data mutation.
- No dependency install or lockfile/package manifest mutation.
- No merge, rebase, reset, stash, clean, branch deletion, or issue close.

## Next

PR #439 is open. Wait for CI, then close issue #235 only after the PR is merged
or owner explicitly approves issue closeout from PR evidence.
