# Issue 221 Feedback Write Auth Current Base

## Status

`PR_OPEN`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-issue221-feedback-write-auth-current-base-v1-20260627`
- Branch: `safe/issue221-feedback-write-auth-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before edits: `7d6ab6c184332d5413700eb08e6790f530000942`
- Issue: <https://github.com/0rl4nd0l/tenn/issues/221>
- PR: <https://github.com/0rl4nd0l/tenn/pull/432>
- PR state at `2026-06-26T18:59:35Z`: OPEN, non-draft,
  `mergeStateStatus=UNSTABLE`; `scan` and `lint-and-test` were IN_PROGRESS.

## Changes

- Added the existing `Depends(require_api_key)` dependency to
  `POST /api/cockpit/feedback`.
- Added the existing `Depends(require_api_key)` dependency to
  `POST /api/cockpit/feedback/flag`.
- Added the existing `Depends(require_api_key)` dependency to
  `POST /api/cockpit/feedback/flags/{report_id}/resolve`.
- Preserved `GET /api/cockpit/feedback/flags` and
  `GET /api/cockpit/feedback/flags/{report_id}` as read/list routes.
- Updated direct Cockpit chat feedback capture to send `X-API-Key` through the
  existing `buildAuthHeaders()` helper.
- Updated Cockpit UI issue capture to send `X-API-Key` from browser
  `cockpit.apiKey` or `NEXT_PUBLIC_API_KEY` when available.
- Added backend tests proving missing/wrong keys are rejected before store or
  service initialization, and matching keys preserve write-route behavior.

## Validation Summary

- Task-card validate: PASS.
- Registry overlap check and claim: PASS.
- Focused backend feedback pytest: 24 passed, 55 deselected, 1 existing warning.
- Ruff touched Python files: PASS.
- Py compile touched Python files: PASS.
- `git diff --check`: PASS.
- Code-reviewer pass: no findings.
- Task-card `check-diff`: PASS.
- Task-card `check-report-artifacts`: PASS.
- Ledger validate: PASS.
- Frontend Vitest: DATA_MISSING; `cockpit-ui/node_modules` is absent and
  `vitest` was not available. No dependency install was run.

## Runtime Functionality Proof

Runtime Functionality Proof result: PARTIAL.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Protected Cockpit feedback write/resolve routes and authenticated direct frontend feedback callers. |
| live output location | `POST /api/cockpit/feedback`; `POST /api/cockpit/feedback/flag`; `POST /api/cockpit/feedback/flags/{report_id}/resolve`; direct Cockpit chat and UI issue capture callers. |
| pre-run max timestamp or count | DATA_MISSING; no live backend, Cockpit runtime, or feedback store queried. |
| post-run max timestamp or count | DATA_MISSING; no live backend, Cockpit runtime, or feedback store queried. |
| rows/files inserted or updated after run start | Zero live data rows/files; source/test/report files only. |
| readiness/gate status | Focused backend route validation passed; frontend runtime test unavailable locally; live runtime smoke not run. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | Live backend/Cockpit runtime was not started, no live feedback store was queried, and frontend Vitest was unavailable because local node dependencies are absent. |

## Safety

- No DB, Qdrant, Redis, news, memory, source PDF, extraction output, prompt,
  gold-label, runtime, model, GPU, service config, or production data mutation.
- No backend/Cockpit service start.
- No dependency install.
- No merge/rebase/reset/stash/clean/prune/delete operations.
