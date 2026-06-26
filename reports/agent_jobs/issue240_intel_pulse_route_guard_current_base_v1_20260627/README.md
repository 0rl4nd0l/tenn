# Issue 240 Intel Pulse Route Guard Current Base

## Status

`PR_OPEN`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-issue240-intel-pulse-route-guard-current-base-v1-20260627`
- Branch: `safe/issue240-intel-pulse-route-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before edits: `7d6ab6c184332d5413700eb08e6790f530000942`
- Issue: <https://github.com/0rl4nd0l/tenn/issues/240>
- Prior local work adopted from:
  `/home/l4nd0/tenn-issue240-intel-pulse-route-guard-v1-20260626`
- PR: <https://github.com/0rl4nd0l/tenn/pull/435>
- PR state at `2026-06-26T19:31:06Z`: OPEN, non-draft,
  `mergeStateStatus=UNSTABLE`; `scan` and `lint-and-test` were IN_PROGRESS.

## Changes

- `GET /api/cockpit/pulse` now registers the existing `require_api_key`
  dependency.
- `GET /api/cockpit/matrix` now registers the existing `require_api_key`
  dependency.
- Missing local API keys are rejected before `CockpitService.get_instance()` is
  called for both routes when `settings.local_api_key` is configured.
- Matching API keys preserve the existing Pulse and Matrix response shapes.
- `getIntelPulse()` and `getDiagnosticMatrix()` send `X-API-Key` through the
  shared `withApiKey()` helper.
- `docs/architecture/19_backend_api_surface.md` documents the guarded route
  contract.

## Validation Summary

- Task-card validate: PASS.
- Registry overlap check and claim: PASS.
- RED backend focused pytest before source fix: 4 failed, 17 passed, 5 warnings.
- GREEN backend focused pytest after source fix: 21 passed, 5 warnings.
- Frontend focused Vitest: BLOCKED, `vitest` not found and
  `cockpit-ui/node_modules` absent.
- Ruff touched Python files: PASS.
- Py compile touched Python files: PASS.
- `git diff --check`: PASS.
- Code-reviewer pass: no findings.

## Runtime Functionality Proof

Runtime Functionality Proof result: PARTIAL.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Intel Pulse and diagnostic Matrix routes require `X-API-Key` when `settings.local_api_key` is configured, and Intel Ops client calls send the configured API key. |
| live output location | Backend routes `GET /api/cockpit/pulse` and `GET /api/cockpit/matrix`; browser client functions `getIntelPulse()` and `getDiagnosticMatrix()`. |
| pre-run max timestamp or count | Live runtime: `DATA_MISSING`; no backend service or production store was probed. Test baseline: route dependency absent and unauthenticated requests reached the service path in focused tests. |
| post-run max timestamp or count | Live runtime: `DATA_MISSING`. Focused tests: missing API key returns 401 before service access; matching API key returns stubbed Pulse/Matrix payloads. |
| rows/files inserted or updated after run start | Live runtime: `DATA_MISSING`. Focused tests: zero live rows/files; no DB/runtime mutation. |
| readiness/gate status | Focused backend route tests, ruff, py_compile, diff check, review, task-card validation, registry claim, and ledger claim pass. Frontend Vitest is blocked by missing local dependencies. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | No live backend/runtime/browser smoke was run; frontend Vitest could not run because local frontend dependencies are absent. |

## Safety

- No financial truth, extraction scoring, diagnostic matrix logic, Signals or
  Memory capability behavior, live DB, Qdrant, Redis, news, memory, source PDF,
  extraction output, prompt, gold-label, runtime, model, GPU, service config, or
  production data mutation.
- No backend/Cockpit service start.
- No dependency install or lockfile/package mutation.
- No merge/rebase/reset/stash/clean/prune/delete operations.
