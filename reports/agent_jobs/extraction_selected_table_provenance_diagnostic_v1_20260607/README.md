# Selected Table Provenance Diagnostic After Count-24

## Verdict

No code repair was made.

The fixed report-local diagnostic ran only for WHC, AZJ, and EDU. It read the
existing count24 result artifacts and existing PyMuPDF parser cache JSON, then
applied the current deterministic table locator and scale detectors through a
dependency shim. It did not invoke Docling/PyMuPDF parsing, LLM extraction,
count-24, count-32, random sampling, broad extraction, backfill, DB, Qdrant,
news, memory, source-PDF edits, or prompt/schema/runtime changes.

## Evidence Summary

| Ticker | Count24 Final Scale | Selected Table Evidence | Decision |
|---|---|---|---|
| WHC | `unknown` | No statement tables were selected from the cached PyMuPDF tables; document-level scale from first 15 cached tables was `unknown`. | Parser/table coverage gap; no scale-binding fix supported. |
| AZJ | `unknown` | Selected income, balance sheet, cash-flow, and share-capital tables had table-local scale `unknown`, but same-page cached text showed `millions`. | Needs no-write pass3a provenance capture before a scale propagation fix. |
| EDU | `unknown` | Selected balance sheet and cash-flow tables had table-local scale `unknown`, but same-page cached text showed raw-dollar `units`; selected income/highlights surfaces were not clean formal statement evidence. | Mixed-source/locator issue; no broad scale propagation. |

The persisted count24 artifacts do not include runtime row refs,
`metric_source_scales`, `metric_scale_sources`, or full Pass 3a LLM outputs.
Those fields are therefore marked `DATA_MISSING` in the diagnostic output rather
than reconstructed.

## Files

- `diagnostic_runner.py`
- `diagnostic_results.json`
- `provenance_summary.json`
- `repair_decision.json`
- `nic_optional_task_prompt.md`
- `status.json`
- `validation.json`

## Repair Decision

The threshold for a safe extension was not met. The diagnostic did not prove the
same missed selected-table scale-binding path in at least two documents with
actual runtime row refs and per-metric source scales.

Count-24 rerun remains blocked. Another random sample is not justified.

## Next Prompt

```text
/goal Build a no-write exact-doc pass3a provenance capture for AZJ and EDU only, using an approved dependency/runtime route that does not write parser cache, DB, Qdrant, news, memory, source PDFs, prompts, schemas, or runtime config. Do not run count-24, count-32, random samples, broad extraction, or backfill. Capture the actual pass3a outputs, row_refs, metric_source_scales, metric_scale_sources, selected table page/header, and final _common_metric_source_scale inputs/outputs. Implement one narrow selected-table scale-binding fix only if both docs prove the same source-bound missed propagation; otherwise keep count-24 blocked and produce the next repair prompt.
```

## Optional NIC Prompt

`nic_optional_task_prompt.md` contains a separate optional task prompt for a
narrow webcast-details noncandidate exclusion. NIC handling was not implemented
in this diagnostic.

## DATA_MISSING

- Runtime row refs.
- Runtime per-metric source scales.
- Runtime metric scale source labels.
- Full Pass 3a LLM outputs.
