# Issue 220 Pending Transcripts Auth Current Base

## Status

`PR_OPEN`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-issue220-pending-transcripts-auth-current-base-v1-20260627`
- Branch: `safe/issue220-pending-transcripts-auth-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before edits: `7d6ab6c184332d5413700eb08e6790f530000942`
- Issue: <https://github.com/0rl4nd0l/tenn/issues/220>
- PR: <https://github.com/0rl4nd0l/tenn/pull/431>

## Changes

- Added the existing `Depends(require_api_key)` dependency to
  `GET /api/commentary/transcripts/pending`.
- Updated `BackendApiClient.get_pending_transcripts()` to forward `X-API-Key`
  via `_api_key_headers()`.
- Added route-level tests proving missing/wrong API keys return 401 before the
  pending index loads, while the matching key preserves the response.
- Added client coverage proving `get_pending_transcripts()` sends the configured
  API key.

## Validation Summary

- Task-card validate: PASS.
- Registry overlap check and claim: PASS.
- `test_local_api_key.py`: 19 passed, 5 existing warnings.
- `TestGetPendingTranscripts`: 2 passed, 1 existing warning.
- Ruff touched files: PASS.
- Py compile touched files: PASS.
- `git diff --check`: PASS.

## Runtime Functionality Proof

Runtime Functionality Proof result: PARTIAL.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Protected pending transcript list route and API-key forwarding from BackendApiClient. |
| live output location | `GET /api/commentary/transcripts/pending`; `BackendApiClient.get_pending_transcripts()`. |
| pre-run max timestamp or count | DATA_MISSING; no live backend or staging store queried. |
| post-run max timestamp or count | DATA_MISSING; no live backend or staging store queried. |
| rows/files inserted or updated after run start | Zero live data rows/files; source/test/report files only. |
| readiness/gate status | Focused route/client validation passed; live runtime smoke not run. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | Live backend/Cockpit runtime was not started, and no live transcript staging store was queried. |

## Safety

- No DB, Qdrant, Redis, news, memory, source PDF, extraction output, prompt,
  gold-label, runtime, model, GPU, service config, or production data mutation.
- No backend/Cockpit service start.
- No merge/rebase/reset/stash/clean/prune/delete operations.
