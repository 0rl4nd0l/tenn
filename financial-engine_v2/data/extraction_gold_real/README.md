# Real ASX Gold Corpus

This directory is the canonical real-document gold corpus for Tenn extraction eval.

Each gold file must stay compatible with the current evaluator contract and include:

- `document_id`
- `source_file`
- `period_type`
- `period_end`
- `currency`
- `scale`
- `metrics`
- `expected_trust`

Conservative labeling rules:

- Copy values from the source PDF only, never from model output.
- Stay inside the current real-gold metric lane: `revenue`, `operating_cash_flow`, `net_debt`.
- Use the exact period, currency, and scale stated by the document.
- Do not infer, reconcile, annualize, or derive missing values.
- If a supported metric is not explicit in the PDF, label that metric as `null` or leave the file unlabeled until verified.

Naming convention:

- Prefer `<ticker>_<period_type>_<period_end>.json`, using lowercase `a`, `h`, or `q`.
- If a document is intentionally awkward/problematic, add a short suffix, for example `_difficult`.

`source_file` guidance:

- Prefer a repo-relative PDF path under `financial-engine_v2/data/asx/docs/...`.
- Keep it pointed at the exact source PDF used for labeling.
- Do not point to a copied excerpt, OCR dump, or model artifact.

Recommended first corpus mix:

- 3 quarterly cash flow docs
- 3 half-year results
- 3 full-year results
- 1 awkward/problematic doc

Current corpus mix after the 2026-05-05 expansion:

- 5 quarterly cash flow docs
- 5 half-year results
- 5 full-year results
- 2 intentionally awkward/problematic docs

Placeholder-only schema example:

```json
{
  "document_id": "<ticker>_<period_type>_<period_end>",
  "source_file": "data/asx/docs/<TICKER>/financial_performance/<source-pdf>.pdf",
  "period_type": "<A|H|Q>",
  "period_end": "<YYYY-MM-DD>",
  "currency": "<AUD|USD|...>",
  "scale": "<units|thousands|millions>",
  "metrics": {
    "revenue": <number-or-null>,
    "operating_cash_flow": <number-or-null>,
    "net_debt": <number-or-null>
  },
  "expected_trust": "<trusted|abstain|quarantine>"
}
```

## Local Measurement Workflow

Use the existing eval-only scripts under `scripts/` to measure the current extraction
pipeline against this corpus without changing runtime architecture:

1. Base eval run

```bash
financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval.py \
  --dataset-dir financial-engine_v2/data/extraction_gold_real \
  --results-json reports/extraction_real_eval_results.json \
  --report-path reports/extraction_real_eval_summary.md
```

2. MLflow-backed local run tracking

```bash
financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval_mlflow.py \
  --dataset-dir financial-engine_v2/data/extraction_gold_real \
  --results-json reports/extraction_real_eval_results.json \
  --report-path reports/extraction_real_eval_summary.md \
  --tracking-dir mlruns \
  --extractor-label multipass_extraction \
  --method-label run_multipass_extraction
```

3. Read-only DuckDB analysis over existing artifacts

```bash
financial-engine_v2/.venv/bin/python scripts/analyze_real_extraction_eval_duckdb.py \
  reports/extraction_real_eval_results.json \
  --summary-path reports/analysis/extraction_real_eval_duckdb_summary.md
```

Artifacts written by the base eval runner:

- detailed JSON: `reports/extraction_real_eval_results.json`
- summary JSON: `reports/extraction_real_eval_results_summary.json`
- canonical scorecard JSON: `reports/extraction_real_eval_results_canonical_scorecard.json`
- summary Markdown: `reports/extraction_real_eval_summary.md`
- per-document CSV: `reports/extraction_real_eval_results_documents.csv`
- per-metric CSV: `reports/extraction_real_eval_results_metrics.csv`
- trust-trigger CSV: `reports/extraction_real_eval_results_trust_triggers.csv`

## Canonical KPI Policy (fixed)

Canonical KPI reporting only accepts runs where all of the following are true:

- `dataset_dir == financial-engine_v2/data/extraction_gold_real`
- `method == docling`
- `strict_method == true`
- `limit == 0`
- `tolerance == 0.01`
- `prompt_variant_id == null`
- `model_override == null`

Runs that do not match this fixed tuple are marked `non_canonical` and remain
valid for exploratory analysis, but they are excluded from canonical KPI rollups.
The exclusion reason list is persisted in `eval_policy.non_canonical_reasons`
inside the JSON artifacts.

Intentional non-goals for this lane:

- no backend request-path integration
- no extraction logic rewiring
- no canonical DB/schema changes
- no orchestrator or memory changes
- no networked tracking service

## 2026-05-05 Conservative Expansion

Source URLs are `DATA_MISSING` for these additions because the local ASX PDF
corpus does not include source URL metadata alongside `data/asx/docs/...` files.

| document_id | company/ticker | source path | source URL | document type | period_type | period_end | currency | scale | why selected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `14d_q_2021-03-31` | 1414 Degrees / 14D | `data/asx/docs/14D/financial_performance/2021-04-30_appendix-4c-quarterly-cashflow-report_408ec763-d97d-4b2b-ad71-170e7a71c9b3.pdf` | DATA_MISSING | Appendix 4C quarterly cash flow report | Q | 2021-03-31 | AUD | thousands | Older non-mining quarterly cash-flow format with only one supported numeric metric clearly present. |
| `a2m_h_2025-12-31` | The a2 Milk Company / A2M | `data/asx/docs/A2M/financial_performance/2026-02-16_appendix-4d-and-1h26-interim-report_008c6807-d8cf-44fe-8087-5d2855d78838.pdf` | DATA_MISSING | Appendix 4D and interim financial report | H | 2025-12-31 | NZD | thousands | Half-year consumer staples report adds NZD currency coverage and ordinary revenue plus operating cash flow labels. |
| `29m_a_2025-12-31` | 29Metals / 29M | `data/asx/docs/29M/financial_performance/2026-02-26_2025-appendix-4e-and-annual-financial-report_0562489a-e22c-4a9d-986a-21f4e9ad358f.pdf` | DATA_MISSING | Appendix 4E annual financial report | A | 2025-12-31 | AUD | thousands | Long full-year mining report with revenue, operating cash flow, and explicit net drawn debt. |
| `rms_h_2025-12-31` | Ramelius Resources / RMS | `data/asx/docs/RMS/financial_performance/2026-02-20_appendix-4d-and-december-2025-half-yearly-financial-report_ef0e8def-850b-4131-808e-481092fe7675.pdf` | DATA_MISSING | Appendix 4D and half-year financial report | H | 2025-12-31 | AUD | thousands | Gold-miner half-year report with financial-review narrative and statutory statement labels. |
| `10x_q_2025-12-31_difficult` | Exultant Mining / 10X | `data/asx/docs/10X/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_28f2a7c8-c61d-4d1b-90ff-4c41d75d23cb.pdf` | DATA_MISSING | Quarterly activities report with Appendix 5B | Q | 2025-12-31 | AUD | thousands | Awkward mining-exploration document with narrative before the Appendix 5B, no revenue line, and explicit no-debt wording outside the table. |
