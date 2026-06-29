# Decisions

## Decision Log

1. Use a fresh sibling worktree from current canonical because the original
   checkout was guard-classified as `STALE_PATH`.
2. Keep remediation control-plane-only.
3. Do not add a visible skill. Add behavior as guard options plus docs/skill
   routing.
4. Preserve full guard detail for high-risk work while making summarized
   fallback detail available for fast/small work.
5. Skip worker delegation because the implementation surface is tightly coupled
   and small enough for one coherent patch.
6. After canonical advanced, replay the allowlisted local diff onto a fresh
   current-base sibling worktree instead of rebasing, merging, or
   cherry-picking the stale-base commit.
7. After PR #460 became two commits ahead and three behind the new canonical
   head, replay the PR diff onto a second fresh current-base sibling worktree
   instead of merging canonical into the PR branch. Stop before any
   force-with-lease update unless Orlando explicitly approves it.
8. After canonical advanced again during v2 validation, replay the validated v2
   diff onto a third fresh current-base sibling worktree and keep the same
   force-with-lease stop boundary.
9. During merge approval preflight, canonical advanced again. Do not merge stale
   PR state; replay the validated v3 diff onto a fourth fresh current-base
   sibling worktree and keep the force-with-lease stop boundary.

## Ledger

- live_ledger_status: `PASS` from guard.
- ledger_update_result: report-local intended entry only unless live append is
  explicitly approved by task-card/owner boundary.
- duplicate_work_classification: `NO_MATCHING_ACTIVE_WORK_FOUND`.
- data_missing: none from guard preflight.

## Host Skill Copy

- Decision: do not mutate `/home/l4nd0/.agents` or other host-global skill
  roots in this lane.
- Reason: the task card is repo control-plane only, and host-global mutation
  requires separate approval.
- Consequence: until the host copy is refreshed, the repo-backed guard command
  may be needed to use `--fallback-detail` and summarized fallback behavior.
