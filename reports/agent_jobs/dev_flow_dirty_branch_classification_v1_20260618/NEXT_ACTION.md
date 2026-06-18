# Next Action

## Taken In This Run

Because some dirty work was genuinely novel, the safe path was to create a clean
sibling worktree from latest canonical and apply only the novel minimal patch.

- Clean worktree:
  `/home/l4nd0/tenn-validation-environment-autonomy-preserve-v1-20260618`
- Branch:
  `control-plane/validation-environment-autonomy-preserve-v1-20260618`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `98e632996aae3bff82627a02b75e64cddd927420`

## Recommended Cleanup Boundary

Do not run broad cleanup, reset, stash, branch deletion, or worktree removal on
the original dirty checkout yet.

Reason: the dirty guidance has now been preserved in a clean PR path, but the
old branch also contains two local commits not on canonical. One of those commits
is a weather-track packet outside this request's approved scope. A broad reset
or branch cleanup would discard more than the five dirty files classified here.

## Safe Cleanup Shape After PR Review

After the preservation PR is merged or explicitly rejected, the original dirty
checkout can be addressed with a separate owner decision:

- Option A: targeted cleanup of only the five dirty/untracked paths classified
  here, preserving local commits.
- Option B: separate audit of the two local ahead commits, then decide whether
  to preserve, park, or discard them.
- Option C: branch/worktree cleanup only after both the dirty files and local
  commits have explicit disposal approval.

Recommended: Option B before any broad cleanup.
