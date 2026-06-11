# Frame

Goal: implement Tenn auto-progress Phase 1 read-only planner for issue #291.

Mode: `REPORT_AUTONOMY` and `ISSUE_291_READONLY_PLANNER` only.

Allowed mutation: repo-backed skill skeleton, task card, and report-local
planner artifacts.

Stop boundary: execution, commits, GitHub writes, product/runtime/data mutation,
service starts, broad validation, branch/worktree deletion, cleanup, reset,
stash, merge, rebase, or cherry-pick.
