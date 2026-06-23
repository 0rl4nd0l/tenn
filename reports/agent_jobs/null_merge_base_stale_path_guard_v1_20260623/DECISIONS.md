# Decisions

## D1: Use A Fresh Control-Plane Worktree

- decision: Use `/home/l4nd0/tenn-null-merge-base-stale-path-guard-v1-20260623`
  from `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- reason: The required first guard command blocked `/home/l4nd0/tenn` as an
  unsafe start path, so no edits were made there.

## D2: Port Only The Regression Fix

- decision: Add `local_branch_name()` and a narrow stale-path branch for a
  checked-out canonical branch whose HEAD differs from canonical.
- reason: This is the exact host-global behavior needed to cover the
  `merge_base_with_canonical=null` stale canonical branch case.

## D3: Keep Duplicate-Work Scope Focused

- decision: No duplicate implementation was started; the task only persists the
  already-proven host-global guard behavior into the repo-backed skill.
- duplicate_work_status: CONTINUE
- reason: A focused open-PR scan for this null-merge-base stale-path guard topic
  found no current duplicate PR before implementation.

## D4: No Runtime Functionality Claim

- decision: This is control-plane guard work only.
- reason: No Tenn product/runtime/data/extraction/count-24, Greyhound runtime,
  host-global mutation, service, DB, source-PDF, prompt, model, or production
  data surface is part of this task.
