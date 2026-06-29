# Next Goal

Recommended next prompt for owner-approved merge:

```text
/goal Review PR #472 for the Tenn docs-only Greyhound project-boundary change from /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629. Verify the latest PR head, checks, mergeability, task-card allowlist, focused docs grep, current canonical overlap, and final git status. If explicitly approved and still green, merge PR #472 according to owner direction. Do not touch Tenn product/runtime/extraction code. Do not touch Greyhound repo files, DBs, systemd units, services, runtime artifacts, branches, worktrees, or GitHub beyond the approved Tenn PR merge.
```

Separate Greyhound relocation prompt, only if physical filesystem cleanup is
desired later:

```text
/goal Greyhound relocation shot 1 only: in the Greyhound repo, produce a no-write relocation manifest for moving Greyhound out of Tenn-named storage paths. Inventory service units, venvs, DB paths, lock/state paths, model paths, artifact roots, active runtime workdirs, ignored/untracked artifacts, branch dirt, rollback commands, and Runtime Functionality Proof requirements. Do not move files, rewrite units, clean artifacts, restart services, mutate DBs, or push.
```
