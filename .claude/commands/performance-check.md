# Performance Check

Evaluates embedding and retrieval performance health. **Read-only** — never modifies system or config.

## When to Use

- Check embedding or retrieval performance
- Diagnose slow RAG/embedding behavior
- Assess GPU memory or throughput health
- Get a performance health report

## Workflow

### 1. Inspect logs

Look for these patterns in backend stdout, Docker logs, or log files under `financial-engine_v2/`:

| Signal | Source | Pattern |
|--------|--------|---------|
| Embedding batch timing | `app.services.pipeline` | `embedding batch %d–%d (%d texts) in %.3fs` (DEBUG) |
| Qdrant search / RAG | `app.services.rag` | `query_rag` INFO with `candidate_count`, `embedding_dim` |
| Request latency | API layer / Uvicorn | Total request duration for `/rag/query` or embedding endpoints |

If the user provides log content or a path, use that. Otherwise suggest where to capture logs (e.g. `docker compose logs backend`) and what time window to use.

### 2. Optionally check GPU status

```bash
python financial-engine_v2/scripts/gpu_runtime_status.py
```

Output: per-GPU memory (`used / total MiB`), aggregate %. Exit 0 = OK, 1 = no GPU, 2 = memory > 95%.

If GPU unavailable or user skips, report "GPU: N/A" and base status on log-derived metrics only.

### 3. Report

## Status Categories

- **HEALTHY**: GPU memory < 85% (or N/A); embedding batch times and throughput normal; no sustained high latency.
- **WARNING**: GPU memory 85–95%; throughput below expectation or variable; occasional slow search.
- **PERFORMANCE DEGRADING**: GPU memory > 95% or repeated OOM; low throughput or many underfilled batches; consistently high latency or timeouts.

If logs are missing, state what's missing and assign status based on available data.

## Report Template

```markdown
## Performance Check Report

**Status:** [HEALTHY | WARNING | PERFORMANCE DEGRADING]

**GPU**
- Memory usage: …% (or N/A)
- Notes: …

**Embedding**
- Throughput estimate: … texts/sec (or N/A)
- Batch efficiency: … (N batches, avg size X / configured Y)

**Search / request**
- Search latency: …
- Request latency: …

**Summary:** One-line summary and optional next step.
```

## Constraints

- **Read-only**: Do not change config, env, database, Qdrant, or run rebuild/index scripts.
- Run only `financial-engine_v2/scripts/gpu_runtime_status.py` for GPU diagnostics.
- Do not install packages, start/stop services, or modify the system.
