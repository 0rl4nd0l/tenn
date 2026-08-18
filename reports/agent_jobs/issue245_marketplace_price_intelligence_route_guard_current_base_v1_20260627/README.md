# Issue 245 Marketplace Price-Intelligence Route Guard Current Base

## Status

`PR_OPEN`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-issue245-marketplace-price-intelligence-route-guard-current-base-v1-20260627`
- Branch:
  `safe/issue245-marketplace-price-intelligence-route-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before edits: `7d6ab6c184332d5413700eb08e6790f530000942`
- Issue: <https://github.com/0rl4nd0l/tenn/issues/245>
- Prior local work adopted from:
  `/home/l4nd0/tenn-issue245-marketplace-price-intelligence-route-guard-v1-20260626`
- PR: <https://github.com/0rl4nd0l/tenn/pull/434>
- PR state at `2026-06-26T19:21:33Z`: OPEN, non-draft,
  `mergeStateStatus=UNSTABLE`; `scan` and `lint-and-test` were IN_PROGRESS.

## Changes

- `financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py`
  now registers the existing `require_api_key` dependency at router level.
- Configured local API-key mode rejects missing or wrong `X-API-Key` before
  tracked-product creation, observation ingest, benchmark-snapshot rebuild, or
  eBay-sync route side effects.
- Matching API keys preserve tracked-product creation, observation ingest,
  benchmark rebuild, and eBay-sync route execution.
- Read routes are guarded in configured-key mode rather than left as public
  undocumented reads.
- `docs/architecture/19_backend_api_surface.md` documents the guarded
  Marketplace price-intelligence route family.

## Validation Summary

- Task-card validate: PASS.
- Registry overlap check and claim: PASS.
- RED focused backend Marketplace auth pytest before source fix: 14 failed,
  2 passed, 20 deselected, 1 warning.
- GREEN focused backend Marketplace auth pytest after source fix: 16 passed,
  20 deselected, 1 warning.
- Ruff touched Python files: PASS.
- Py compile touched Python files: PASS.
- `git diff --check`: PASS.
- Code-reviewer pass: no findings.

## Runtime Functionality Proof

Runtime Functionality Proof result: PARTIAL.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Marketplace price-intelligence reads and mutations require `X-API-Key` when `settings.local_api_key` is configured; missing or wrong keys are rejected before state mutation or eBay-sync side effects. |
| live output location | Backend route family `/api/cockpit/marketplace/price-intelligence/*`; isolated test `COCKPIT_STATE_DB` temp SQLite state. |
| pre-run max timestamp or count | Live runtime: `DATA_MISSING`; no backend service or production state store was probed. Test baseline: empty temp state DB. |
| post-run max timestamp or count | Live runtime: `DATA_MISSING`. Focused tests: rejected states did not call `_service`; matching-key flow created one temp tracked product, one observation, one benchmark snapshot, and one stubbed eBay-sync response. |
| rows/files inserted or updated after run start | Live runtime: `DATA_MISSING`. Focused tests: zero service calls for rejected states, isolated temp DB writes only for matching-key success flow. |
| readiness/gate status | Focused route tests, ruff, py_compile, diff check, review, task-card validation, registry claim, and ledger claim pass. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | No live backend/runtime smoke was run and no production Marketplace state store was inspected. |

## Safety

- No live DB, Qdrant, Redis, news, memory, source PDF, extraction output,
  prompt, gold-label, runtime, model, GPU, service config, or production data
  mutation.
- No backend/Cockpit service start.
- No dependency install.
- No merge/rebase/reset/stash/clean/prune/delete operations.
