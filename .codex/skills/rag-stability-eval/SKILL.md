---
name: rag-stability-eval
description: Run the RAG stability harness, parse the latest summary, and report STABLE, MINOR DRIFT, or MAJOR DRIFT without modifying Qdrant or the database.
---

# RAG Stability Eval

Use this skill for read-only stability checks of retrieval behavior.

## Workflow

1. Run:

```bash
python financial-engine_v2/scripts/evaluate_rag_stability.py
```

2. Read:

- `financial-engine_v2/reports/rag_stability/latest_summary.json`

3. Report these metrics:

- `avg_rank_drift`
- `avg_score_drift`
- `drift_percentage`

## Status Rules

- `STABLE`: no previous run or within thresholds
- `MINOR DRIFT`: drift present but within thresholds
- `MAJOR DRIFT`: `avg_rank_drift > 2` or `avg_score_drift > 0.15`

## Constraints

- Never modify the database or Qdrant.
- Never auto-run rebuild workflows.
- Rebuild can only be mentioned as a human decision.
