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
- summary Markdown: `reports/extraction_real_eval_summary.md`
- per-document CSV: `reports/extraction_real_eval_results_documents.csv`
- per-metric CSV: `reports/extraction_real_eval_results_metrics.csv`
- trust-trigger CSV: `reports/extraction_real_eval_results_trust_triggers.csv`

Intentional non-goals for this lane:

- no backend request-path integration
- no extraction logic rewiring
- no canonical DB/schema changes
- no orchestrator or memory changes
- no networked tracking service
