# Dev Flow Reset Shot 1 Native Wrappers

State: DONE_WITH_RISK

## Objective

Create the Shot 1 instruction-only Tenn wrapper skills, templates, task card,
and report bundle for the native hands-off development workflow.

## Constraints And Unsafe Actions

- Control-plane docs, repo skills, task card, templates, and report artifacts
  only.
- No product/runtime/data/extraction mutation.
- No source PDFs, gold labels, DB, Qdrant, Redis, news, memory, prompts, schema,
  runtime/model/GPU config, services, or count-24 packet changes.
- No cleanup automation, worker spawning scripts, host-global hooks, branch
  deletion, worktree deletion, merge, rebase, cherry-pick, reset, stash, clean,
  prune, or broad validation.
- GitHub mutation is deferred until local validation passes and PR creation is
  the only GitHub write.

## Files Touched

See `IMPLEMENTATION.md`.

## Files Intentionally Not Touched

- Product, runtime, data, extraction, model, GPU, prompt, source-PDF,
  gold-label, DB, Qdrant, Redis, news, memory, schema, service, and backfill
  paths.
- Existing skills outside the new wrapper directories.
- Host-global Codex files.
- GitHub issues and PRs before local validation.
- Branches and worktrees other than creating the requested clean sibling
  worktree and branch for this implementation.

## Unsafe Actions Avoided

- No cleanup automation.
- No worker spawning scripts.
- No host-global hook changes.
- No merge, rebase, cherry-pick, reset, stash, clean, prune, branch deletion, or
  worktree deletion.

## Validation

See `VALIDATION.md`.

Local validation passed. Remaining risk is external to the local diff: GitHub PR
creation and any remote CI/review state happen after this report is committed.

## Next Recommended Prompt

See `NEXT_STEPS.md`.
