# RAG Stability Eval

Runs the RAG stability evaluation harness, interprets drift metrics, and outputs a structured stability report. **Read-only** — never modifies database, Qdrant, or auto-runs rebuild.

## Instructions

1. **Run the harness** (from repo root):
   ```bash
   python financial-engine_v2/scripts/evaluate_rag_stability.py
   ```
2. **Parse** `financial-engine_v2/reports/rag_stability/latest_summary.json`.
3. **Interpret** and report using the format below.

## Summary Schema

- `avg_rank_drift`: Average top-5 position changes per query vs previous run.
- `avg_score_drift`: Average absolute score difference per position across queries.
- `drift_percentage`: Percentage of queries with any rank change.

If no previous run exists, fields may be `null` — report **STABLE** (no comparison) and skip drift suggestions.

## Thresholds

| Metric | Minor drift | Major drift |
|--------|------------|-------------|
| avg_rank_drift | > 0 | > 2 |
| avg_score_drift | > 0 | > 0.15 |
| drift_percentage | > 0 | — |

**Status:**
- **STABLE**: No previous run, or avg_rank_drift ≤ 2 and avg_score_drift ≤ 0.15.
- **MINOR DRIFT**: Some drift but within thresholds.
- **MAJOR DRIFT**: avg_rank_drift > 2 or avg_score_drift > 0.15.

## Report Format

```markdown
## RAG Stability Report

**Stability status:** [STABLE | MINOR DRIFT | MAJOR DRIFT]

**Metrics:**
| Metric             | Value |
|--------------------|-------|
| avg_rank_drift     | …     |
| avg_score_drift    | …     |
| drift_percentage   | …%    |

**Checks:**
- Embedding model file matches: [confirmed from run / not applicable / verify manually]
- No dimension mismatch errors: [confirmed from run output / not applicable]

**Recommendations:** (only if drift exceeds thresholds)
- Verify embedding model unchanged: `financial-engine_v2/reports/runtime_embedding_model.txt`
- Verify vector baseline: `financial-engine_v2/scripts/verify_vector_baseline.py`
- Consider rebuild only after human approval: `financial-engine_v2/scripts/rebuild_rag_qdrant_index.py`
```

## Confirmation Rules

- **Embedding model matches**: If harness exited 0 with no HTTP 5xx → "confirmed from run (backend up)". If run failed → "verify manually".
- **No dimension mismatch**: If no "dimension mismatch" in output and POST /rag/query succeeded → "confirmed from run output". Otherwise → "check backend logs".

## Constraints

- **Never** modify the database or Qdrant.
- **Never** auto-run or recommend automatic execution of the rebuild script — only suggest it as a human decision.
- Read-only: run harness → read summary → interpret → output report.
