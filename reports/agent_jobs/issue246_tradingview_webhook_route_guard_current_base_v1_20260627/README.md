# Issue 246 TradingView Webhook Route Guard Current Base

## Status

`PR_OPEN`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-issue246-tradingview-webhook-route-guard-current-base-v1-20260627`
- Branch: `safe/issue246-tradingview-webhook-route-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD before edits: `7d6ab6c184332d5413700eb08e6790f530000942`
- Issue: <https://github.com/0rl4nd0l/tenn/issues/246>
- Prior local work adopted from:
  `/home/l4nd0/tenn-issue246-tradingview-webhook-route-guard-v1-20260626`
- PR: <https://github.com/0rl4nd0l/tenn/pull/433>
- PR state at `2026-06-26T19:08:58Z`: OPEN, non-draft,
  `mergeStateStatus=UNSTABLE`; `scan` and `lint-and-test` were IN_PROGRESS.

## Changes

- `POST /api/cockpit/tv/alert` now fails closed with `503` when
  `TV_WEBHOOK_TOKEN` is unset.
- Configured webhook mode rejects missing or wrong
  `X-TradingView-Webhook-Token` before alert persistence.
- Matching configured webhook token still accepts and persists the alert.
- `GET /api/cockpit/tv/alerts` now registers `require_api_key`, so configured
  local API-key mode rejects missing or wrong `X-API-Key`.
- `docs/architecture/19_backend_api_surface.md` documents the external webhook
  token contract and the guarded alert-history read contract.

## Validation Summary

- Task-card validate: PASS.
- Registry overlap check and claim: PASS.
- Focused backend TradingView route pytest: 8 passed, 1 existing warning.
- Ruff touched Python files: PASS.
- Py compile touched Python files: PASS.
- `git diff --check`: PASS.
- Code-reviewer pass: no findings.
- Task-card `check-diff`: PASS.
- Task-card `check-report-artifacts`: PASS.
- Ledger validate: PASS.

## Runtime Functionality Proof

Runtime Functionality Proof result: PARTIAL.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Unconfigured or incorrectly tokened TradingView alert ingestion is rejected before persistence, and alert-history reads require the local API key when configured. |
| live output location | Backend routes `POST /api/cockpit/tv/alert` and `GET /api/cockpit/tv/alerts`; alert file `settings.data_root/tv_alerts.json`. |
| pre-run max timestamp or count | Live runtime: `DATA_MISSING`; no service or production alert store was probed. Test baseline: no `tv_alerts.json` in isolated `tmp_path`. |
| post-run max timestamp or count | Live runtime: `DATA_MISSING`. Focused tests: rejected states wrote zero files; matching-token state wrote one temp alert. |
| rows/files inserted or updated after run start | Live runtime: `DATA_MISSING`. Focused tests: zero temp writes for rejected states, one temp file for valid configured token. |
| readiness/gate status | Focused route tests, ruff, py_compile, diff, code-review, task-card validation, registry, and ledger gates pass. Live runtime smoke not run. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | No live backend/runtime smoke was run and no production alert store was inspected. |

## Safety

- No frontend/browser secret exposure.
- No live alert store, DB, Qdrant, Redis, news, memory, source PDF, extraction
  output, prompt, gold-label, runtime, model, GPU, service config, or
  production data mutation.
- No backend/Cockpit service start.
- No dependency install.
- No merge/rebase/reset/stash/clean/prune/delete operations.
