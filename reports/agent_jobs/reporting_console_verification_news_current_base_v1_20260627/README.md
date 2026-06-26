# Reporting Console, Verification, And News Current-Base Replacement

Status: `PARTIAL_READY_FOR_DRAFT_PR`

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
task card, no dependency install was run. Any PR from this branch must stay
draft until GitHub CI passes.

The first push attempt was blocked by missing local pre-push hook tools
(`financial-engine_v2/.venv/bin/ruff` and `financial-engine_v2/.venv/bin/pytest`).
The task card allows a missing-hook bypass only for draft-PR publication with
the blocker recorded.

## Files Intentionally Not Touched

- Backend API/RAG/storage/runtime files.
- Financial truth, memory, source-label, parser, extraction, DB, Qdrant, Redis,
  news-store, model, GPU, service, and production-data surfaces.
- PR #133 branch/history.

## Closeout

Issues #45, #47, and #49 must remain open until the replacement PR is merged
into canonical and merge containment is verified.
