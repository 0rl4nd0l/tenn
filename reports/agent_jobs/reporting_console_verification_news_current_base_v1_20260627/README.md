# Reporting Console, Verification, And News Current-Base Replacement

Status: `PR_READY_GATE_AVAILABLE_CI_GREEN`

## Summary

This task ports the narrow PR #133 fixes onto current canonical HEAD
`7d6ab6c184332d5413700eb08e6790f530000942` so issues #45, #47, and #49 can move
forward without merging the now-conflicting old branch.

## Changes

- `cockpit-ui/app/layout.tsx`: renders Vercel Analytics only when `VERCEL=1` or
  `NEXT_PUBLIC_ENABLE_VERCEL_ANALYTICS=1`.
- `cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx`: uses
  stable sentinel Select values for optional recent-run and saved-review
  selectors.
- `cockpit-ui/components/cockpit/news/news-screen.tsx`: maps bounded News
  lookback selections to the existing `/rag/query` `date_from` field.
- Focused tests were added or extended for Verification selector control state
  and News lookback request payloads.

## Superseded Work

- PR #133 remains open but is currently `mergeStateStatus=DIRTY` /
  `mergeable=CONFLICTING` against
  `migration/clean-runtime-baseline-reconstruct-v1`.
- This branch supersedes PR #133's patch path only. It does not close or delete
  PR #133.

## Validation

See `VALIDATION.md`.

Local executable frontend validation is `DATA_MISSING`: this fresh worktree has
no `cockpit-ui/node_modules`, and `vitest` / `eslint` are unavailable. Per the
task card, no dependency install was run. GitHub CI later passed on PR #447, so
the ready-for-review gate is available while runtime/browser proof remains
`DATA_MISSING`.

The first push attempt was blocked by missing local pre-push hook tools
(`financial-engine_v2/.venv/bin/ruff` and `financial-engine_v2/.venv/bin/pytest`).
The task card allows a missing-hook bypass only for draft-PR publication with
the blocker recorded.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Local Cockpit browser/runtime omits Vercel Analytics by default, Verification review selectors avoid controlled/uncontrolled warnings, and News search requests include `date_from` for bounded lookbacks. |
| live output location | Browser console and network requests for `/`, `/verification`, and `/news`; `/rag/query` request payload. |
| pre-run max timestamp or count | DATA_MISSING; no live Cockpit runtime/browser smoke was started in this task. |
| post-run max timestamp or count | DATA_MISSING; no live Cockpit runtime/browser smoke was started in this task. |
| rows/files inserted or updated after run start | 0 live runtime rows/files; repository files changed only. |
| readiness/gate status | PR #447 opened; GitHub checks passed (`lint-and-test`, `scan`) and mergeStateStatus is `CLEAN`; local frontend executable validation DATA_MISSING due absent dependencies. |
| exact command/query used | `git diff --check`; `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md --repo-root .`; attempted `corepack pnpm --dir cockpit-ui exec vitest ...`, `eslint ...`, and `tsc --noEmit` blocked because commands were unavailable. |
| result | DATA_MISSING |
| remaining blocker | No live browser/runtime proof and no local frontend dependency toolchain; merge/issue close still requires review or merge approval plus canonical containment. |

result: DATA_MISSING

## Files Intentionally Not Touched

- Backend API/RAG/storage/runtime files.
- Financial truth, memory, source-label, parser, extraction, DB, Qdrant, Redis,
  news-store, model, GPU, service, and production-data surfaces.
- PR #133 branch/history.

## Closeout

PR: https://github.com/0rl4nd0l/tenn/pull/447

Issues #45, #47, and #49 must remain open until PR #447 is merged into
canonical and merge containment is verified.
