# Scale Table Source Evidence After Count-24

## Verdict

MQR `results-of-meeting` handling is integrated in the current branch through
commit `b5537f933f2b7b31a1cab8dea0f4204ba2ac8360`; it is not an ancestor of
`origin/migration/clean-runtime-baseline-reconstruct-v1`.

No additional code repair was made in this phase. WHC, AZJ, EDU, and NIC share
the `scale_unknown` gate, but the source audit found different root causes:

- WHC: source scale exists visually on statement tables as `$'000`, but the
  text/table path does not expose those headers.
- AZJ: source scale is machine-readable as `$m`, with nearest-$100k rounding
  notes; runtime selected-table provenance is needed before changing scale
  propagation.
- EDU: source evidence is mixed, with `$'000` summary pages and raw-dollar main
  financial statements.
- NIC: one-page webcast-details announcement, not a financial report; this is
  a document-family policy gap, not a scale-table repair.

Because no single source-bound repair pattern appears in at least two audited
cases, the safe extension threshold was not met.

## Files

- `mqr_integration_audit.json`
- `source_evidence.json`
- `root_cause_classification.json`
- `repair_decision.json`
- `status.json`
- `validation.json`

## Next Prompt

```text
/goal Build a report-local selected-table provenance diagnostic for WHC/AZJ/EDU only. Do not run count-24, count-32, random samples, broad extraction, or backfill. For each document, capture the runtime-selected table/page, table header, row_refs, per-metric source_scale, final payload scale decision, and why _common_metric_source_scale did or did not set scale. Implement at most one narrow source-bound fix only if the diagnostic proves the same missed selected-table scale-binding pattern in at least two docs; otherwise produce the exact next repair prompt. Also prepare a separate optional NIC webcast-details noncandidate task, but do not implement it in the scale diagnostic unless explicitly approved.
```

## Hard Stops

No count-24 rerun, count-32, random sample, broad extraction, backfill, full
ticker-universe extraction, DB/Qdrant/news/memory mutation, source PDF edit, or
prompt/gold-label/runtime/schema change was performed.
