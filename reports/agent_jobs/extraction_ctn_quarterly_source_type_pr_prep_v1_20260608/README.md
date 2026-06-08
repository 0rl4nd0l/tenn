# CTN Quarterly Source-Type PR Prep

State: `RUNNING`

## Objective

Prepare and publish a draft PR for the CTN-only quarterly source-type
precedence safe extension.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-ctn-quarterly-source-type-pr-v1-20260608`
- Branch:
  `safe/extraction-ctn-quarterly-source-type-precedence-pr-v1-20260608`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD:
  `d97b3a2a1e9c755b536bb862ce3b47b9e28266db`
- CTN safe-extension commit cherry-picked cleanly from `c7a80b8c` to
  `25a0f7b25e72fff541aea6ba6f8d8505c4f624f5`.

## Scope

Draft PR only. No merge, no ready-for-review transition, no issue edits, no
labels, no broad extraction, no count runs, no service routes, and no data-store
mutation.

## Validation

- Task card validate: passed.
- Registry read-only: passed; no active jobs.
- Duplicate PR check: no existing PR found for the PR branch or CTN commits.
- Focused pytest: passed via isolated `uv` environment:
  `19 passed, 1 warning`.
- CTN-only saved-artifact scorecard replay: passed; previous
  `period_source_mismatch` replayed as `ok`, observed gain `+1` document and
  `+6` non-null canonical metrics.
- No extraction, count run, backfill, service route, or data-store mutation was
  run.

## PR

Pending.
