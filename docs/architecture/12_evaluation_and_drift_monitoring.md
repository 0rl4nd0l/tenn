# Evaluation and drift monitoring

This doc describes how we evaluate RAG retrieval and monitor for drift. The focus today is **consistency** (run-to-run stability), not **correctness** (whether retrieved docs are the “right” answers). A future gold-dataset flow for precision/recall is planned and noted as a placeholder.

---

## RAG stability harness: purpose

The RAG stability harness (`financial-engine_v2/scripts/evaluate_rag_stability.py`) answers:

- **Did retrieval stay consistent?** — Same fixed test queries are run against `POST /rag/query`; results are compared to the previous run. We care about rank and score drift, not whether the top-5 are “correct” by human judgment.

So:

- **Consistency**: Are we getting the same (or very similar) top-5 document IDs and scores for the same queries between runs? This catches embedding-model changes, index rebuilds, or config drift that would change retrieval behavior.
- **Correctness**: Are the retrieved documents actually the right ones for the query? That is **not** what this harness measures; it is reserved for a future gold-dataset evaluation (see below).

The script is **read-only**: it does not modify the database, Qdrant, or run any rebuild; it only calls the backend `/rag/query` endpoint and writes report files.

---

## Output file locations

All paths are under `financial-engine_v2/` (script’s `REPO_ROOT`).

| Output | Path | Description |
|--------|------|-------------|
| Timestamped run | `reports/rag_stability/<timestamp>.json` | Full run: all 15 queries, top-5 doc IDs, scores, candidate/filtered counts. Used as “previous run” for the next comparison. |
| Latest summary | `reports/rag_stability/latest_summary.json` | Compact summary for dashboards/CI: drift metrics and run timestamp. |

Example timestamp format: `20250228T143022Z`. The harness compares the current run to the most recent **other** JSON file in the same directory (by filename); that comparison is what drives the drift metrics and CI pass/fail.

---

## `latest_summary.json` usage

`latest_summary.json` is the canonical artifact for “how did the last run compare to the previous one?”. Schema:

| Field | Type | Meaning |
|-------|------|---------|
| `avg_rank_drift` | number or `null` | Average number of top-5 positions that changed per query (vs previous run). `null` if no previous run. |
| `avg_score_drift` | number or `null` | Average absolute score difference per position across all queries. `null` if no previous run. |
| `drift_percentage` | number or `null` | Percentage of queries that had any rank change. `null` if no previous run. |
| `timestamp` | string | UTC timestamp of the run (e.g. `20250228T143022Z`). |

Use it to:

- **CI / automation**: Read this file after the harness runs to decide pass/fail (or rely on the script’s exit code; see below).
- **Dashboards / alerts**: Plot or alert on `avg_rank_drift`, `avg_score_drift`, or `drift_percentage` over time.
- **Debugging**: After a failing run, inspect the summary to see whether drift was rank-heavy, score-heavy, or both.

If there was no previous run, all drift fields are `null`; the run is still written and the script exits 0 (no comparison, so no drift to fail on).

---

## CI `rag-stability-check` behavior

In `.github/workflows/backend-ci.yml`, the job `rag-stability-check`:

1. **Depends on** the `invariants` job (architecture and cursor-rule tests).
2. **Starts** Qdrant and Ollama as services; installs backend deps; pulls the embedding model (`nomic-embed-text`); ensures the Qdrant collection exists (read-only: no DB writes); starts the backend with uvicorn.
3. **Runs** `financial-engine_v2/scripts/evaluate_rag_stability.py` from `financial-engine_v2/backend` (so the script path is `../scripts/evaluate_rag_stability.py`).

**What it tests:**

- All 15 fixed test queries hit `POST /rag/query` and return 200.
- No query returns 0 hits (script sets `any_zero_hits` and exits 1 if any do).
- If a **previous** run exists in `reports/rag_stability/*.json`, drift is computed; the script exits 1 if thresholds are exceeded.

**Thresholds (script exit code 1):**

| Condition | Failure |
|-----------|---------|
| Any query has 0 hits | Exit 1 |
| `avg_rank_drift` > 2 | Exit 1 |
| `avg_score_drift` > 0.15 | Exit 1 |

So CI fails on empty retrieval for any test query or on major rank/score drift. Minor drift (e.g. small score changes, or rank changes below the above limits) does not fail the job.

---

## Next planned: gold dataset (precision/recall)

Planned but not yet implemented: a **gold dataset** of (query, ticker?, expected document IDs or relevance labels) to measure:

- **Precision / recall** of retrieval (e.g. are the “right” docs in the top-k?).
- **Correctness** of answers when used with a reader/LLM, if we choose to evaluate that.

This would complement the stability harness (consistency) with an explicit correctness signal. Placeholder only—no paths, schema, or CI contract defined yet.

---

## Multipass extraction accuracy eval

A separate eval harness tests the accuracy of the financial metric extraction pipeline. This is distinct from RAG stability; it measures whether the LLM extracts the correct numeric values from real PDFs.

### Harness location

- Test file: `backend/tests/test_extraction_eval.py`
- Config: `backend/tests/eval_config.json`
- Fixtures: `backend/tests/eval_fixtures/*.json`
- Output (gitignored): `backend/tests/eval_results/`

### Two modes

| Mode | How to run | What it tests |
|------|-----------|---------------|
| Unit mode (default) | `pytest backend/tests/test_extraction_eval.py` | Harness structure: fixture loading, metric_matches tolerance, expected_nulls counting logic |
| Live eval | `pytest -m live_eval backend/tests/test_extraction_eval.py` | Full pipeline against real LLM — asserts accuracy >= thresholds |

### Fixture inventory

Current repo fixture pool: 13 JSON fixtures under `backend/tests/eval_fixtures/`.

| Fixture | Ticker | Period type | Asserted metrics | Per-fixture min accuracy | Notes |
|---------|--------|-------------|-----------------|--------------------------|-------|
| `ANZ_H_2025-03-31.json` | ANZ | Half-year (H) | 9 | 0.80 | Bank/interim fixture. 1 expected-null assertion. |
| `AZJ_H_2025-12-31.json` | AZJ | Half-year (H) | 10 | 0.00 | Known unsolved Identity-H CID font encoding issue; threshold intentionally disabled. |
| `BHP_A_2021-06-30.json` | BHP | Annual (A) | 9 | 0.80 | Annual USD fixture. 1 expected-null assertion remains. |
| `CSL_H_2025-12-31.json` | CSL | Half-year (H) | 10 | 0.80 | USD healthcare fixture. |
| `EQR_Q_2025-12-31.json` | EQR | Quarterly (Q) | 4 | 0.80 | Appendix 5B quarterly. 5 expected-null assertions for absent income-statement metrics. |
| `FMG_H_2025-12-31.json` | FMG | Half-year (H) | 10 | 0.60 | Threshold reduced for current extraction variance on this filing. |
| `GRE_Q_2024-12-31.json` | GRE | Quarterly (Q) | 4 | 0.80 | Appendix 5B quarterly. 5 expected-null assertions. |
| `MIN_H_2025-12-31.json` | MIN | Half-year (H) | 10 | 0.80 | Appendix 4D + interim report. |
| `RMS_H_2025-12-31.json` | RMS | Half-year (H) | 10 | 0.70 | Appendix 4D fixture with one expected-null assertion. |
| `SEG_H_2025-12-31.json` | SEG | Half-year (H) | 8 | 0.80 | Non-mining half-year fixture. |
| `TCL_H_2025-12-31.json` | TCL | Half-year (H) | 9 | 0.80 | Infrastructure/toll-road half-year fixture. 1 expected-null assertion. |
| `TLS_H_2025-12-31.json` | TLS | Half-year (H) | 10 | 0.80 | Telecom half-year fixture. |
| `WOW_H_2026-01-04.json` | WOW | Half-year (H) | 10 | 0.80 | Retail half-year fixture with non-calendar period end. |

**Quarterly fixtures** (GRE, EQR): Both are value-asserted with hand-verified cash-flow values from PDF. `expected_nulls` asserts that income statement metrics (`revenue`, `ebit`, `np_attributable`, `net_debt`, `shares_outstanding`) are correctly identified as absent in Appendix 5B documents. Cash-flow tolerances remain 1% for flow metrics and 0.1% for `cash_end`.

### Accuracy thresholds

Defined in `eval_config.json`:

| Threshold | Value |
|-----------|-------|
| `min_accuracy_overall` | 0.85 |
| `warn_threshold` (soft floor, emits UserWarning) | 0.80 |
| `min_accuracy_per_metric.operating_cf` | 0.90 |
| `min_accuracy_per_metric.revenue` | 0.85 |
| `min_accuracy_per_metric.period_end` | 1.00 |

### PDF availability

All fixture PDFs live at `financial-engine_v2/data/asx/docs/` and are present in the working environment. This path is gitignored; PDFs are not tracked in the repository.

### Adding new fixtures

When promoting a fixture from structural-only to value-asserted, or adding a new ticker:

1. Read the source PDF directly (use PyMuPDF/`fitz`) — do not infer values.
2. Perform an arithmetic cross-check (`cash_start + operating_cf + investing_cf + financing_cf + fx = cash_end`).
3. Store values in absolute native units (e.g. multiply `$A'000` values by 1000).
4. Remove a metric from `expected_nulls` when adding it to `metrics`.
5. Update the fixture inventory table in this doc.

---

## Real-document gold eval pilot

The real-document pilot is a separate measurement lane for hand-labelled ASX filings. It is additive only: it does not change extraction behavior, canonical database writes, routing, or financial truth rules.

### Corpus location and contract

- Corpus path: `financial-engine_v2/data/extraction_gold_real/`
- Labeling guide: `financial-engine_v2/data/extraction_gold_real/README.md`
- Current required fields per gold file:
  - `document_id`
  - `source_file`
  - `period_type`
  - `period_end`
  - `currency`
  - `scale`
  - `metrics`
  - `expected_trust`
- Current supported real-gold metric scope:
  - `revenue`
  - `operating_cash_flow`
  - `net_debt`

Rules:

- Values must come from the source PDF, not model output.
- Keep `source_file` pointed at the exact repo-relative source PDF when possible.
- Do not infer, reconcile, or derive missing values in this corpus.
- Keep the pilot in the existing corpus path; do not create a second gold location.

### Base eval run

The canonical local runner is:

```bash
financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval.py \
  --dataset-dir financial-engine_v2/data/extraction_gold_real \
  --results-json reports/extraction_real_eval_results.json \
  --report-path reports/extraction_real_eval_summary.md
```

### Parser backend and published benchmarks

Optional: pass `--parser-backend` (for example `docling` or `pymupdf`; see `scripts/run_real_extraction_eval.py --help` for the full set) to compare PDF parser stacks under the same LLM and gold corpus without changing application code.

Recorded example: docling vs pymupdf on the 10-document real-gold corpus, including commands, environment audit notes, and comparative DuckDB output — [reports/benchmark_2026-04-10/BENCHMARK_REPORT.md](../../reports/benchmark_2026-04-10/BENCHMARK_REPORT.md).

Artifacts:

- JSON results: `reports/extraction_real_eval_results.json`
- Summary JSON: `reports/extraction_real_eval_results_summary.json`
- Markdown summary: `reports/extraction_real_eval_summary.md`
- Per-document CSV: `reports/extraction_real_eval_results_documents.csv`
- Per-metric CSV: `reports/extraction_real_eval_results_metrics.csv`
- Trust-trigger CSV: `reports/extraction_real_eval_results_trust_triggers.csv`

### Local MLflow tracking

Local-only experiment tracking is available through the wrapper:

```bash
financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval_mlflow.py \
  --dataset-dir financial-engine_v2/data/extraction_gold_real \
  --results-json reports/extraction_real_eval_results.json \
  --report-path reports/extraction_real_eval_summary.md \
  --tracking-dir mlruns \
  --model-label "<label>" \
  --profile-label "<label>"
```

Properties:

- File-backed only (`mlruns/` in the repo root)
- No remote tracking server
- No backend runtime instrumentation
- Logs corpus path/fingerprint when available, summary metrics, per-metric accuracy, trust-trigger counts, and eval artifacts

If you already have eval artifacts and only want to register them in MLflow without rerunning extraction:

```bash
financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval_mlflow.py \
  --reuse-existing \
  --results-json reports/extraction_real_eval_results.json \
  --report-path reports/extraction_real_eval_summary.md \
  --tracking-dir mlruns
```

### Read-only DuckDB analysis

Use the local analysis helper to slice existing eval artifacts without touching canonical tables or request paths:

```bash
financial-engine_v2/.venv/bin/python scripts/analyze_real_extraction_eval_duckdb.py \
  reports/extraction_real_eval_results.json \
  --summary-path reports/analysis/extraction_real_eval_duckdb_summary.md
```

Pass **multiple** result JSON paths (space-separated) to compare two or more runs in one analysis (for example docling vs pymupdf artifacts); see the benchmark report linked in [Parser backend and published benchmarks](#parser-backend-and-published-benchmarks).

The script is intentionally read-only and answers questions such as:

- which metrics fail most
- which documents fail most
- wrong vs missing vs abstained vs quarantine distribution
- failure clusters by ticker and period type when that metadata is available
- trust-trigger summaries
- what failure patterns appear by period type or trust outcome

It reads eval JSON artifacts only and writes an optional local markdown summary.

---

## Prompt registry and prompt×model matrix

The extraction pipeline resolves its prompt text through `app.services.prompt_registry`:

- `PromptBundle(id, pass1, pass3a, pass3b)` is a frozen dataclass with content-addressable `sha256[:16]` hashing.
- `multipass_extraction` registers the canonical bundle at import time under the id `"default"`.
- `PROMPT_HASH` is derived from `resolve("default").compute_hash()` and is **byte-identical** to the legacy formula `sha256((_PASS1 + _PASS3A + _PASS3B).encode()).hexdigest()[:16]`. This is an invariant — historical rows in `extraction_runs.prompt_hash` must remain linkable. A regression test in `backend/tests/test_prompt_model_matrix.py` asserts this.
- `resolve(bundle_id)` raises `KeyError` on an unknown id (fail-fast, per `rules/bug-resolution.md`); there is no silent fallback.

### Matrix runner

`financial-engine_v2/scripts/run_prompt_model_matrix.py` enumerates (prompt_variant × model) cells and POSTs each to `/api/extraction-eval/real-gold`.

Ordering is **model-major**: outer loop over models, inner loop over prompt variants. This matches the llama.cpp router mode (`--models-max 1`), where only one GGUF is in VRAM at a time — keeping the model pinned across successive variants avoids repeated swaps.

Per-cell HTTP payload:

```json
{
  "limit": <int>,
  "tolerance": <float>,
  "method": "auto|docling|pymupdf|anthropic",
  "strict_method": false,
  "prompt_variant_id": "default",
  "model_override": "qwen2.5-14b-instruct"
}
```

`model_override` is threaded through every LLM call via `metadata.requested_model`, which `app.services.llm._resolve_runtime_from_metadata` already honors.

The runner writes an incremental JSON report (one rewrite per completed cell) so a long run is never lost midway. Each report carries `run_metadata` (git branch/commit/dirty + python + timestamp) from `scripts/_run_metadata.build_run_metadata`.
