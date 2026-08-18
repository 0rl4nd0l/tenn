# Dev Flow Ledger Runtime Handoff Replay V1

## Summary

PR #367 was open but dirty against latest canonical after PRs #368, #370, #373,
and #374 landed. This replay preserves the still-relevant task-ledger runtime,
ledger templates, focused tests, original PR #367 report evidence, and
repo-native `tenn-handoff` guidance on a clean sibling branch.

## Replay Branch

- source PR: #367
- source branch: `control-plane/agent-ledger-runtime-handoff-v1-20260617`
- replay branch: `control-plane/agent-ledger-runtime-handoff-replay-v1-20260618`
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- canonical head at replay start:
  `44137442fad9cd47bfa938113dbb400b394c69df`
- clean worktree:
  `/home/l4nd0/tenn-agent-ledger-runtime-handoff-replay-v1-20260618`

## Conflict Resolution

The replay keeps canonical changes from the later merged control-plane PRs:

- PR #368 docs freshness and model routing
- PR #370 OpenCode worker bridge
- PR #373 OpenCode worker bridge safety hardening
- PR #374 validation-environment autonomy guidance

Only PR #367's ledger runtime, session trace, task-ledger templates, handoff
skill, and matching report evidence were replayed.

## Original Dirty Checkout

The original checkout was not modified. Its five dirty paths were previously
classified as superseded by canonical, while unrelated local commits on that
branch remain an owner cleanup boundary.

## Scope Guard

No Tenn product, runtime, data, extraction, source-PDF, gold-label, prompt,
schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or count-24 paths
were intentionally touched.
