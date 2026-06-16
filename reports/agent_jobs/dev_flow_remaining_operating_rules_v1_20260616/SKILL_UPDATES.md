# Skill Updates

Updated wrapper skills:

- `tenn-issue`: added `DATA_MISSING` evidence grading and counter-lineage mode
  before broad issue framing for metric/count/status confusion.
- `tenn-review-board`: added denominator/freshness challenge requirements for
  metric/evaluation decisions.
- `tenn-fix`: blocks implementation from headline metrics until denominator,
  filters, exclusions, freshness, and pipeline stage are understood.
- `tenn-worker`: requires `worker id` in `WORKER_RESULT.md` ledger fields.
- `tenn-explain`: added full Counter Lineage Mode and `COUNTER_LINEAGE.md`
  durable-output behavior.
- `tenn-code-reviewer`: checks counter-lineage when metric/evaluation reporting
  changes.
- `tenn-improve-codebase-architecture`: explicitly says execution mode requires
  a task card and exact scope.

Verified existing `tenn-git-guard` already contains branch superiority, stale
work classification, Task Ledger preflight, duplicate-work classification, base
selection order, configured `registry_root` live-ledger resolution, and hook
cooperation with host/repo backend guards.
