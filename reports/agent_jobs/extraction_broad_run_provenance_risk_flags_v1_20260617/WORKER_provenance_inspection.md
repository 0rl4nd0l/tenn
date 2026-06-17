# WORKER_RESULT: Provenance Inspection

- Parent task: `extraction_broad_run_provenance_risk_flags_v1_20260617`
- Lane: `Provenance`
- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- Task status: `DONE_READ_ONLY`
- Ledger status: `DATA_MISSING`

## Files Inspected

- `docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`

## Findings

- `run_one()` previously copied only metrics, period, scale, confidence, non-null count, and sanity fields.
- Pass 4 already builds richer fields: `row_refs`, `provenance`, `field_provenance`, `metric_source_scales`, and `metric_scale_sources`.
- Parent implementation should surface existing fields only and keep `multipass_extraction.py` untouched.

## DATA_MISSING

- Exact `table_index`, `table_caption`, `table_headers`, metric-specific `period_column`, and `value_cell_text` are not in final Pass 4 payload.
- `field_provenance.excerpt` is row-level text and may duplicate `row_ref`.

## Recommended Action

Use compact per-metric evidence plus explicit missing fields in broad-run output. Keep full table markdown out of the default record unless a later task approves a larger artifact.
