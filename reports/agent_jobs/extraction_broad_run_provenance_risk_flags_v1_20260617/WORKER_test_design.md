# WORKER_RESULT: Test Design

- Parent task: `extraction_broad_run_provenance_risk_flags_v1_20260617`
- Lane: `Evaluation`
- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- Task status: `DONE_READ_ONLY_TEST_DESIGN`
- Ledger status: `NOT_CHECKED` for exact inspect-only worker scope

## Files Inspected

- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`

## Recommended Tests

- Synthetic helper test for per-metric provenance surfacing.
- Synthetic helper test for scale/magnitude risk flags.
- Synthetic `compute_summary()` rollup test for provenance and risk distributions.

## RED Strategy

Use only synthetic records and helper imports. Do not run extraction, PDFs, LLM clients, services, stores, or broad samples.

## Parent Result

Parent added the recommended RED tests and captured the expected failures before implementation. The focused and full script tests now pass.
