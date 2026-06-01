# Extraction Payload Gate Blocking Summary

## Summary

This safe-extension slice makes `pre_persistence_scorecard_gate_v1` actionable
for broader confirmed-metric payload reviews.

The gate already failed closed. It now also reports every blocking document and
every document missing actual payloads, so the next operator run can fill gaps
without relying on the bounded `blocking_examples` preview.

## Scope

- Lane: Evaluation, with Financial Truth support.
- Branch: `safe/extraction-payload-gate-blocking-summary-v1-20260531`.
- Worktree:
  `/home/l4nd0/tenn-extraction-payload-gate-blocking-summary-v1-20260531`.
- Execution mode: SAFE EXTENSION MODE.
- Runtime/backend/GPU work: not performed.
- Production data access: not used.

## Result

- Added `blocking_document_count`.
- Added complete `blocking_document_summary`.
- Added `missing_actual_document_count`.
- Added complete `missing_actual_document_ids`.
- Preserved existing gate status, blocker counts, `blocking_examples`, and
  canonical write/backfill prohibitions.

## Sample Artifact

Sample command used the existing payload-scorecard CLI and previous synthetic
actuals sample to write
`reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/gate_actionability_sample.json`.

Sample result:

- Gate status: `fail`
- Blocking documents: `15`
- Documents missing actual payloads: `7`
- First missing actual payload documents:
  `dxs_20251231_h`, `eqr_q4_fy2026_appendix5b`,
  `gre_q4_fy2025_appendix5b`, `min_2025h1_appendix4d`,
  `qbe_20250630_h`

## Full Goal Status

This improves the repeatability and actionability of broader scorecard evidence
needed before third-canary or all-ticker graduation claims. It does not
complete the full metric extraction objective because current actual payloads,
approved canary execution, and graduation evidence remain open.
