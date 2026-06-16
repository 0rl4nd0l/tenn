# Dev Flow Operating Constitution Refinement

State: DONE_WITH_RISK

## Objective

Refine Tenn's concise `AGENTS.md` constitution and native dev-flow wrapper
skills with the new operating principles.

## Evidence Used

- PR #355: merged.
- Current base: `e33a64a8ee9795535acf2bdc0bd2bcc0fd09eb18`
  on `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Wrapper skills from PR #355 exist on base.
- Read-only registry: `ok: true`, `read_only: true`, `lock_acquired: false`.
- Related branch/PR/worktree audit: no newer unmerged implementation was
  adopted; current base already includes the relevant merged PRs.

## Constraints

- Control-plane docs, repo skills, templates, task card, and report artifacts
  only.
- No product/runtime/data/extraction mutation.
- No host-global Codex mutation.
- No cleanup, merge, rebase, reset, stash, prune, branch deletion, or worktree
  deletion.
- GitHub mutation limited to opening a PR after local validation passes.

## Files Touched

See `AGENTS_UPDATES.md`, `SKILL_UPDATES.md`, and `HOOK_INTEGRATION.md`.

## Validation

See `VALIDATION.md`.

Local validation passed. Remaining risk is remote CI/review after PR creation.

## Unsafe Actions Avoided

- No product/runtime/data/extraction mutation.
- No count-24 packet changes.
- No host-global Codex mutation.
- No cleanup, branch deletion, worktree deletion, merge, rebase, reset, stash,
  prune, or broad validation.
