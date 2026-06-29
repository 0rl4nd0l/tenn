# Next Goal

Recommended next prompt to finish publication:

```text
/goal Continue publishing the Tenn docs-only Greyhound project-boundary branch from /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629. The branch is clean and rebased, but pre-push is blocked because financial-engine_v2/.venv is missing ruff and pytest. If approved, use TENN_ALLOW_MISSING_HOOK_TOOLS=1 for this push only and open a draft PR against migration/clean-runtime-baseline-reconstruct-v1. Do not touch Tenn product/runtime/extraction code. Do not touch Greyhound repo files, DBs, systemd units, services, runtime artifacts, branches, worktrees, or GitHub beyond the approved branch push and draft PR.
```

Separate Greyhound relocation prompt, only if physical filesystem cleanup is
desired later:

```text
/goal Greyhound relocation shot 1 only: in the Greyhound repo, produce a no-write relocation manifest for moving Greyhound out of Tenn-named storage paths. Inventory service units, venvs, DB paths, lock/state paths, model paths, artifact roots, active runtime workdirs, ignored/untracked artifacts, branch dirt, rollback commands, and Runtime Functionality Proof requirements. Do not move files, rewrite units, clean artifacts, restart services, mutate DBs, or push.
```
