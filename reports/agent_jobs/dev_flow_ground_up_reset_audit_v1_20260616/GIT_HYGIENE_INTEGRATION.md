# Git Hygiene Integration

Git Hygiene should become a required backend guard named `tenn-git-guard`, not a
separate command Orlando must remember.

## Preflight For Every Command

Every `/issue`, `/review-board`, and `/fix` run should do:

1. Identify worktree path, branch, HEAD, base, remote, and upstream.
2. Compare base relationship to `origin/migration/clean-runtime-baseline-reconstruct-v1`.
3. Read status with normal Git; if that fails, try explicit worktree gitdir; if
   both fail, stop with `DATA_MISSING`.
4. Run `python3 scripts/agent_job_registry.py list-active --read-only`.
5. Classify dirty files as task/report, hook/config, product/runtime/data,
   extraction/source, generated, user-owned unknown, or DATA_MISSING.
6. Search related PRs/issues read-only before suggesting mutation.
7. Detect owner-boundary paths and stale/superseded branches.

## Post-Run Enforcement

Every command should end with:

- changed-path guard;
- task-card validate and `check-diff` when safe;
- report-local `STATE.md` or `README.md`;
- worker result check if subagents ran;
- no unreported dirty files in worker worktrees;
- next goal or blocked state.

## Stop-Hook Integration

Stop hooks should be backstops only. The workflow should discover dirty-state,
registry, and allowlist problems before work starts. Stop hooks then verify:

- active task card still validates;
- current diff is inside allowlist;
- active registry status is visible;
- report/STATE exists when needed;
- no unexplained dirty state remains.

## Cleanup Rule

No cleanup unless explicitly approved. Git guard may recommend:

- ignore;
- preserve;
- review;
- park;
- later clean.

It may not delete, prune, stash, reset, merge, rebase, cherry-pick, push, or
mutate GitHub by default.
