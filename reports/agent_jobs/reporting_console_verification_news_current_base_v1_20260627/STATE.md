# State

status: `PR_READY_GATE_AVAILABLE_CI_GREEN`

## Current State

- Worktree:
  `/home/l4nd0/tenn-issues45-47-49-reporting-cleanliness-current-base-v1-20260627`
- Branch: `safe/issues45-47-49-reporting-cleanliness-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- Registry: claimed
- Registry release: complete
- PR: #447
- GitHub checks: `lint-and-test` pass, `scan` pass
- Merge state: `CLEAN`
- Issues: #45, #47, #49
- Prior PR: #133, superseded because it is now conflicting

## Validation State

- Task card validate: pass
- Registry list/check-overlap/claim: pass
- `git diff --check`: pass
- Task-card `check-diff`: pass
- Focused Vitest: `DATA_MISSING`, command unavailable because
  `cockpit-ui/node_modules` is absent
- Targeted ESLint: `DATA_MISSING`, command unavailable because
  `cockpit-ui/node_modules` is absent
- TypeScript noEmit: `DATA_MISSING`, local TypeScript binary unavailable

## Next Safe Action

Mark PR #447 ready for review if the post-metadata-push GitHub checks remain
green and mergeStateStatus remains `CLEAN`. Merge or close issues only after
review or merge approval and canonical merge containment.
