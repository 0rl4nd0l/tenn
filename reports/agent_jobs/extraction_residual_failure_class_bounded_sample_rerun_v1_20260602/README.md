# Extraction Residual Failure Class Bounded Sample Rerun V1

## Verdict

Exactly one bounded broad extraction validation sample was run after residual failure-class hardening commit `902d03b4aa43`. The run used count `8`, seed `20260601`, docs root `/data/asx/docs`, and local llama.cpp router `:8001` with `model:qwen2.5-14b-instruct`.

No full extraction, broad backfill, canary run, worker queue, direct SQL write, Qdrant/news/memory mutation, canonical truth promotion, source-PDF mutation, prompt change, gold-label change, or runtime/model/GPU config change beyond minimal readiness/startup was run.

## Result

Baseline before this fix: `ok=4`, `ok_low_confidence=0`, `failed=4`.

Current sample: `ok=6`, `ok_low_confidence=2`, `failed=0`.

Delta: strict OK `+2`, low-confidence `+2`, failed `-4`.

The hardening improved broad robustness in this bounded sample by eliminating failures, but two low-confidence cases remain and this is not ticker-universe graduation evidence.

## Sample

Candidate filter retained `21163` of `28633` financial-performance PDFs and excluded `7470`.

Sampled documents:

- `ok` `CRS` `data/asx/docs/CRS/financial_performance/2021-10-29_quarterly-activities-appendix-5b-cash-flow-report_e92ad3bc-d9a0-4916-8867-78635487bea8.pdf` metrics=5/10 confidence=1.0
- `ok_low_confidence` `NSM` `data/asx/docs/NSM/financial_performance/2023-03-15_half-yearly-report-and-accounts_db3717b6-fe21-4e62-9ca7-31de22d40f50.pdf` metrics=6/10 confidence=0.695
- `ok` `AZJ` `data/asx/docs/AZJ/financial_performance/2023-02-13_aurizon-network-pty-ltd-half-year-report_95c99aec-a4c1-4d6e-bd89-ee7347218124.pdf` metrics=9/10 confidence=0.926
- `ok` `ABE` `data/asx/docs/ABE/financial_performance/2022-09-30_annual-report-to-shareholders_0414ebcc-8398-4948-b741-4716d66f1480.pdf` metrics=8/10 confidence=0.852
- `ok` `NWM` `data/asx/docs/NWM/financial_performance/2025-04-30_quarterly-activities-appendix-5b-cash-flow-report_90e69a82-c609-4ca9-83ce-ac9c15d17a7a.pdf` metrics=5/10 confidence=1.0
- `ok` `CRS` `data/asx/docs/CRS/financial_performance/2023-09-28_full-year-statutory-accounts_6b3754ce-d0ee-46b7-9bed-e07182d39fa2.pdf` metrics=6/10 confidence=1.0
- `ok` `NVU` `data/asx/docs/NVU/financial_performance/2024-01-31_quarterly-appendix-4c-cash-flow-report_e5987b49-a90d-445d-a338-619990c4069c.pdf` metrics=4/10 confidence=0.8
- `ok_low_confidence` `WBC` `data/asx/docs/WBC/financial_performance/2024-02-19_westpac-1q24-update_3899b7ba-df77-4788-be1c-a6d5d65f947f.pdf` metrics=2/10 confidence=0.667

## Failure Taxonomy

Failures: none.

Low-confidence cases:

- `NSM` `data/asx/docs/NSM/financial_performance/2023-03-15_half-yearly-report-and-accounts_db3717b6-fe21-4e62-9ca7-31de22d40f50.pdf` confidence=0.695 metrics=6/10: real_half_year_report_low_confidence_metric_coverage.
- `WBC` `data/asx/docs/WBC/financial_performance/2024-02-19_westpac-1q24-update_3899b7ba-df77-4788-be1c-a6d5d65f947f.pdf` confidence=0.667 metrics=2/10: quarterly_update_low_confidence_metric_coverage.

## Remaining Risk

This sample is broad robustness evidence only. It does not prove gold accuracy, full ticker-universe readiness, broad backfill safety, or canonical truth promotion readiness. AZJ remains broader parser/metric-coverage work outside this sample even though the sampled AZJ document returned `ok` here.

## Validation Notes

The exact task-card path supplied by the user was absent initially, so this session created `docs/agent_tasks/extraction_residual_failure_class_bounded_sample_rerun_v1_20260602.md` from the user-provided constraints before validating and claiming it. The older `extraction_residual_failure_gate_bounded_sample_rerun_v1_20260602` report was inspected but not reused because it belongs to commit `32e39089` and predates `902d03b4`.

`/api/health` verified backend liveness, but API-visible loaded commit remains DATA_MISSING because the health route only returns `{"status":"ok"}` and `/api/cockpit/config` exposes branch, not commit. Current-turn git HEAD and backend process cwd are captured in `preflight.json`.
