# Decisions

## Use Exact Synthetic Fixture

Decision: use an exact synthetic report artifact instead of searching for or
running another extraction sample.

Reason: the prior `NEXT_GOAL.md` allowed either an existing saved artifact with
mixed source scales or an exact synthetic fixture committed as a test/report
artifact. The synthetic path exercises the risk helper deterministically without
runtime or canonical data mutation.

## Exercise Multiple Risk Rules In One Record

Decision: create one accepted-output record that triggers:

- `all_checked_metrics_below_minimum`
- `mixed_metric_source_scales`
- `payload_scale_differs_from_metric_source_scale`
- `metric_source_scale_missing`
- `metric_revenue_ratio_high`

Reason: a single compact fixture gives machine-readable positive coverage for
summary rollups and individual accepted-output risk flags.

## Keep Source Code Unchanged

Decision: do not add or edit source-code tests in this slice.

Reason: the requested continuation is bounded to a no-extraction fixture/replay
and report artifact. Source-code test hardening can be a later explicit slice.

## No Subagents

Decision: no new subagents for this slice.

Reason: prior worker notes already identified the exact risk surface, and the
current task is a narrow fixture replay with no code change or contested runtime
inspection.
