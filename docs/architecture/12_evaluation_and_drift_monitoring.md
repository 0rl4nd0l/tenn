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
