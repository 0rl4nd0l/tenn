---
name: performance-check
description: Perform a read-only performance health check for embeddings, retrieval, request latency, and optional GPU status using logs and gpu_runtime_status.py.
---

# Performance Check

Use this skill to assess performance health without changing system state.

## Workflow

1. Inspect relevant logs for:
   - embedding batch timing
   - RAG/search timing
   - request latency
2. If useful and safe, run:

```bash
python financial-engine_v2/scripts/gpu_runtime_status.py
```

3. Classify status:
   - `HEALTHY`
   - `WARNING`
   - `PERFORMANCE DEGRADING`

## Report

Return a short report with:

- status
- GPU memory usage or `N/A`
- embedding throughput estimate or `N/A`
- batch efficiency
- search/request latency
- one-line summary

## Constraints

- Read-only.
- Do not rebuild, reindex, reconfigure, or install anything.
