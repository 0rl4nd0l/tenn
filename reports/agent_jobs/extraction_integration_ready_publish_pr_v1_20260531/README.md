# Extraction Integration Ready Publish PR

## Summary

Publishing the clean integration branch for review as a draft PR.

## Scope

- Branch: `integrate/extraction-metric-ontology-gate-v1-20260531`
- Worktree: `/home/l4nd0/tenn-extraction-integration-ready-v1-20260531`
- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Repository: `0rl4nd0l/tenn`
- Integration commit before rebase: `687b912b74b9`
- Integration commit after rebase onto current base: `1962cc49`
- Publish task evidence commit after rebase: `631c32d0`
- Lane: Evaluation, supporting Financial Truth

## Pre-Publish Evidence

- Task-card validation: passed
- Registry overlap check: passed
- Registry claim: passed
- GitHub CLI installed: `gh version 2.4.0+dfsg1`
- GitHub authentication: logged in as `0rl4nd0l`
- Existing PR for head branch before publish: none
- Branch relation before publish task card commit: `0` behind / `1` ahead of `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base branch advanced by PR #130 before draft PR creation. The integration
  branch was rebased onto `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at `6caa3e72`, resolving the only overlap in `docs/claude/STATE.md`.
- Post-rebase focused ontology/scorecard tests: `61 passed, 1 warning`
- Post-rebase broader extraction eval tests: `388 passed, 1 deselected, 6 warnings`

## Publication

- Remote branch pushed:
  `origin/integrate/extraction-metric-ontology-gate-v1-20260531`
- Draft PR: https://github.com/0rl4nd0l/tenn/pull/131
- PR title: `[codex] prepare integration-ready metric gate branch`
- PR base: `migration/clean-runtime-baseline-reconstruct-v1`
- PR state after creation: open draft, mergeable, `scan` success,
  `lint-and-test` in progress at `2026-05-31T07:13:00Z`
- Registry release: passed at `2026-05-31T07:14:14.576578Z`

## Boundaries

This publish task permits only pushing the isolated integration branch and
opening one draft PR. It does not authorize runtime startup/reload, canary
execution, document submission, backfill, DB/Qdrant/source-PDF mutation,
parser/prompt/schema changes, Cockpit UI work, model/GPU config changes, or
full-objective closure.

## Current Status

Draft PR opened and registry claim released. GitHub CI is still in progress for
`lint-and-test`; the full 10-item extraction objective remains open.
