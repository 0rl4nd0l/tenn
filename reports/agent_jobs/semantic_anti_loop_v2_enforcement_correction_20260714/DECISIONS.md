# Decisions

- Keep Tenn V1-compatible by default; require V2 only in repositories that set
  the opt-in hook environment and matching instructions.
- Treat the task registry and decision ledger as separate state machines.
- Let normal V2 release validate and append the current run's decision candidate
  under the same shared lock; reserve standalone append for authorized seeds.
- Permit a material candidate to override only a concurrent
  `LOOP_GUARD_STOP`. Concurrent resolved, missing-data, conflict, or explicit
  blocking decisions stop release.
- Reuse an identical latest-head decision only for an idempotent retry after a
  release-receipt write failure.
- Preserve offline/prospective track isolation unless an explicit dependency is
  declared.
- Suppress unclassified Git hooks during V2 publication only after explicit
  validation has passed.
