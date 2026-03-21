# Performance Skill

## Source Trace
- `docs/ops/03_model_tiering_m40_24gb.md` (Confirmed — referenced)
- `docs/ops/01_nvml_host_stabilization_runbook.md` (Confirmed — referenced)
- `docs/ops/02_ollama_m40_validation_and_mitigation.md` (Confirmed — referenced)
- `docs/architecture/01_system_overview.md` (Confirmed — router weights)
- `docs/ops/README.md` (Confirmed — llama.cpp preference, GPU-first)
- `docs/ops/cockpit_chat_latency_analysis.md` (Confirmed — referenced)
- `docs/ops/known_good_baseline_profiles.md` (Confirmed — referenced)

---

## Performance Hierarchy

1. **GPU inference (llama.cpp on M40)** — preferred for all workloads
2. **Ollama (M40)** — financial-engine backend; Maxwell-specific mitigations required
3. **CPU fallback** — supported but not the expected production path; do not normalize in new guidance

Do not invent performance numbers. Use `docs/ops/known_good_baseline_profiles.md` for reference values.

---

## Model Router Weights

The self-optimizing router scores models using:
```
score = latency×0.4 + throughput×0.3 + error×0.2 + queue×0.1 + gpu×0.1
```

Changing these weights affects routing behavior globally. Any weight change requires:
1. Re-validation of routing behavior across finance task categories
2. RAG stability verification
3. Documented rationale

Source: `docs/architecture/01_system_overview.md`

---

## GPU Guidance (Tesla M40, 24GB VRAM)

- Maxwell architecture (no FP16 acceleration) — batch operations preferred over streaming
- NVML stabilization must be confirmed before loading models; see `docs/ops/01_nvml_host_stabilization_runbook.md`
- Ollama M40 mitigation required; see `docs/ops/02_ollama_m40_validation_and_mitigation.md`
- Model tiering for 24GB VRAM; see `docs/ops/03_model_tiering_m40_24gb.md`
- Current profile: `llama3.1:8b` for generation, `nomic-embed-text` for embeddings (Inferred — verify against `~/.openclaw/openclaw.json`)

**Never reduce batch size without confirming VRAM is the bottleneck.**

---

## Embedding Performance

- Embedding batch size: default `EMBEDDING_BATCH_SIZE=32`
- Embeddings use Ollama or local sentence-transformers depending on config
- Deterministic vector IDs enable upsert without re-embedding; avoid changing ID generation logic
- Docling uses GPU acceleration for complex PDFs; see `docs/ops/docling_gpu_tesla_m40.md`

---

## Inference Endpoint Selection

| Workload | Preferred Endpoint | Config Variable |
|----------|--------------------|-----------------|
| Agent/coding sessions | llama.cpp | `LLAMACPP_URL` |
| Financial RAG generation | llama.cpp or Ollama (via router) | `LLM_URL` |
| Embedding (financial engine) | Ollama `nomic-embed-text` | `OLLAMA_URL` |
| Deep reasoning tasks | deep_reasoning role via router | (automatic) |

---

## Performance Investigation Protocol

1. **Measure before changing** — gather latency baseline from `docs/ops/cockpit_chat_latency_analysis.md` or a fresh benchmark run.
2. **Identify bottleneck** — is it inference, retrieval, extraction, or network?
3. **Check GPU utilization** — `nvidia-smi dmon -s u`
4. **Check queue depth** — Redis queue depth for Celery tasks
5. **Check router feedback** — `ROUTER_FEEDBACK_ENABLED=true`; analyze routing decisions
6. **Make one change at a time** — verify improvement before stacking changes.
7. **Document results** — record in `docs/ops/` with before/after; do not overwrite existing baseline values.

---

## What NOT to Do

- Do not reduce model quality (tier down) to solve latency without confirming the latency source.
- Do not increase `EMBEDDING_BATCH_SIZE` without confirming VRAM headroom.
- Do not disable GPU in production to "simplify" a performance investigation.
- Do not fabricate benchmark numbers or latency improvements.
- Do not change router scoring weights without running the full validation sequence.
