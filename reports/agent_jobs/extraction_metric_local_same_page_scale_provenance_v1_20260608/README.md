# Metric-Local Same-Page Scale Provenance Capture

State: DONE_WITH_RISK

## Objective

Build a no-write metric-local same-page scale provenance capture for AZJ plus
one additional clean same-page candidate from the fixed scale-table harness.

## Verdict

No production extraction repair was made.

AZJ remains the only clean same-page scale-propagation candidate in current
artifacts. Its selected formal statement pages carry same-page `$m` evidence,
but runtime metric source scale fields are missing and the common-scale trace
returns `unknown`.

EDU remains fail-closed because selected surfaces are mixed/unclean.

CXO is a clean scale-known control. Parser-cache tables show explicit `$A'000`
scale evidence on the quarterly cash-flow pages, but current accepted-output
artifacts do not expose runtime selected table/row refs, metric source scales,
metric scale source labels, or common-scale trace. CXO therefore cannot serve
as the second same-root repair proof.

## Artifacts

- `case_candidate_audit.json`
- `provenance_capture.json`
- `repair_decision.json`
- `status.json`
- `validation.json`

## Count-24 / Count-32 Decision

Count-24 rerun is not justified.

Count-32 remains blocked.

## DATA_MISSING

- Second clean same-page failure with metric-local row/page/source-scale trace.
- Runtime row refs for accepted CXO metrics.
- Runtime metric source scales for accepted CXO metrics.
- Runtime metric scale source labels for accepted CXO metrics.
- Runtime common-scale input/output trace for accepted CXO metrics.

## Unsafe Actions Avoided

- No count-24 rerun.
- No count-32.
- No random sample.
- No broad extraction/backfill.
- No full ticker-universe extraction.
- No DB/Qdrant/Redis/news/memory mutation.
- No source PDF edits.
- No prompt/gold-label/runtime/schema/model/GPU changes.
- No broad scale inference.
- No truth gate loosening.

## Next Prompt

```text
/goal Build an exact-doc no-write runtime provenance capture for CXO plus one additional clean scale-known control from the fixed scale-table harness, without running count-24, count-32, random samples, broad extraction, backfill, DB/Qdrant/news/memory writes, source-PDF edits, prompt/gold/runtime/schema changes, or truth-gate loosening. Capture row_refs, selected table/page, row/cell text, table-local scale, same-page scale, document-level scale, metric_source_scales, metric_scale_sources, and _common_metric_source_scale input/output. Implement no production repair unless two clean cases prove the same source-bound root cause.
```
