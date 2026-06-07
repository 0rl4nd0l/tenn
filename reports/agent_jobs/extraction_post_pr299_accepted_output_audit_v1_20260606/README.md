# Post-PR299 Accepted-Output Audit

Generated: 2026-06-07T03:36:26Z

State: DONE_WITH_RISK. Integration review completed; accepted-output audit
completed; one narrow quarantine fix implemented and validated. Risk remains
because DXC/LBL accepted rows in the committed count-16 artifact are unsafe and
the artifact omits exact row refs/provenance for accepted rows.

## Integration Result

The source branch `safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`
was reviewed and locally integrated cleanly in
`/home/l4nd0/tenn-post-pr299-integration-accepted-output-audit-v1-20260607` via
fast-forward from remote canonical `9436d1d32de0da5423b8edcfc7efc883ccac3fd6`
to `55209fb52c31661f00d35db8044efdf9456195cc`.

The dirty baseline checkout on `tmp/sloppy-fix-demo` was not used for edits.
Source branch diff scope was task cards, reports, extraction candidate taxonomy,
selected-table scale repair, tests, and docs. No source PDFs were in the diff.

## Accepted-Output Audit Table

| Ticker | Classification | Quarantine | Summary |
| --- | --- | --- | --- |
| DXC | needs quarantine; scale-binding bug; selected-table mismatch | yes | Accepted values used document-level `millions` against a page 26 `$'000` table; `ebit` maps to `Net operating income`, not EBIT. |
| LBL | needs quarantine; selected-table mismatch; scale-binding bug; DATA_MISSING | yes | Accepted values line up with historical FY25 rows and over-scaled A$000/$m presentation data, not the 1H FY26 period. |
| AZJ | ok but report-only; rounding-policy issue | no | Values match `$m` source rows, but the report states values are rounded to nearest $100,000 and precision/trust metadata is missing. |

## Narrow Fix Implemented

`financial-engine_v2/backend/app/services/multipass_extraction.py` now rejects
`Net operating income` as a source label for canonical `ebit` through the
existing metric-label mismatch gate. A focused test was added in
`financial-engine_v2/backend/tests/test_multipass_extraction.py`.

## Validation

- Task card validate: passed.
- Focused pytest after integration: `179 passed`.
- Focused pytest after the accepted-output guard: `3 passed, 175 deselected`.
- Final focused pytest after the guard: `180 passed`.
- py_compile: passed.
- ruff: passed.
- JSON validation: passed.
- git diff --check: passed.
- task-card check-diff: passed.
- No source PDFs staged or in diff.
- Registry/list-active: active jobs empty; command reports `read_only=false`.

## Count-24 Decision

Count-24 is not justified. DXC and LBL accepted rows are unsafe until contained
or repaired; AZJ needs rounding/precision provenance before broad promotion.

## DATA_MISSING

- The committed count-16 artifact omits row refs, provenance, markdown tables,
  and metric source scales for accepted rows.
- Post-fix runtime outcome for DXC/LBL/AZJ was not measured.
- Safe read-only registry proof is unavailable; list-active reports
  `read_only=false`.
- Docling structured table objects for LBL hidden PowerPoint chart data were not
  inspected to avoid parser/cache side effects.

## Unsafe Actions Avoided

No count-24/count-32, random sample rerun, broad extraction, backfill,
production DB/Qdrant/news/memory mutation, source PDF edits, prompt/gold-label/
runtime/schema changes, or unrelated cleanup ran.

## Next Recommended Prompt

Create a bounded accepted-output containment task that performs no broad sample,
verifies DXC/LBL with no-write single-doc/debug artifacts only if approved, and
adds targeted quarantine for presentation/hidden-chart period-column mismatches
before any count-24 approval packet.
