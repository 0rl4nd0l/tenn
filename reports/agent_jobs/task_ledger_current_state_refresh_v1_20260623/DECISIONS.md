# Decisions

## D1: Use A Fresh Canonical Worktree

Decision: create `/home/l4nd0/tenn-task-ledger-current-state-refresh-v1-20260623`
from `origin/migration/clean-runtime-baseline-reconstruct-v1`.

Reason: the session cwd was not a Git worktree, and the inherited plan required
starting from canonical at or after PR #388 merge commit
`d8be998e0d1aae992c12b1d5bf7ca42229f46508`.

## D2: Treat PR #387 As Canonical History

Decision: do not continue `control-plane/task-ledger-status-refresh-v1-20260623`.

Reason: GitHub shows PR #387 merged. The branch is not an active lane and is
superseded by canonical state for this follow-up.

## D3: Export From Live Ledger Even Though History Shrinks

Decision: append the current task to the resolved live ledger and run
`export-summary --write`, producing a committed snapshot from live ledger state.
The first export had one raw live entry, and the final export has two raw
entries for this task: `implementation_started` and `done`.

Reason: the requested task explicitly allowed live append and asked to make live
versus committed ledger state truthful. Older PR #380/#382/#383/#385/#386
entries were hand-curated committed evidence, not live-ledger entries, so they
were not preserved in the live export.

## D4: Record Historical Backfill As Follow-Up Only

Decision: do not backfill older verified control-plane PRs into the live ledger
in this task.

Reason: backfill would be a broader ledger-history reconstruction task. This
lane is limited to current-state drift after PR #388.
