# Domain Skill: Model Routing

## Source Trace
- `docs/architecture/model-routing.md` (Confirmed)
- `docs/architecture/01_system_overview.md` (Confirmed)
- `docs/ops/03_model_tiering_m40_24gb.md` (Confirmed — referenced)

---

## Key Files

| File | Role |
|------|------|
| `financial-engine_v2/backend/app/config/model_routing.yaml` | **Source of truth for routing config** |
| `financial-engine_v2/backend/app/services/router.py` | Router entrypoint |
| `financial-engine_v2/backend/app/services/router_metrics.py` | Runtime metrics store |
| `financial-engine_v2/backend/app/services/router_state.py` | Runtime state collector |
| `financial-engine_v2/backend/app/services/router_optimizer.py` | Adaptive optimizer |
| `financial-engine_v2/backend/app/services/llm.py` | Routed LLM facade (external interface) |

Operational changes go in `model_routing.yaml`, not in code.

---

## Five Roles

| Role | Purpose | Default Queue | Current Model (local) |
|------|---------|--------------|----------------------|
| `router_model` | Lightweight classification, short reasoning fallback | `llm_cpu` | `llama3.1:8b` |
| `coding_model` | Repo/code/patch-oriented prompts | `llm_gpu` | `llama3.1:8b` |
| `reasoning_model` | Financial analysis, RAG synthesis, extraction, research | `llm_gpu` | `llama3.1:8b` |
| `deep_reasoning_model` | Long-form or explicitly deep analysis | `llm_gpu` | `llama3.1:8b` |
| `embedding_model` | All embedding work | `embed` | `nomic-embed-text` |

Local profile base URL: `http://127.0.0.1:11434` (Ollama). Verify against `model_routing.yaml` before assuming.

---

## Celery Queue Topology (unchanged by router)

| Queue | Tasks |
|-------|-------|
| `ingest` | `backfill_ticker`, `download_pdf` |
| `embed` | `llm_embed_texts` |
| `score` | Deterministic scoring jobs |
| `llm_gpu` | `process_document`, GPU-bound reasoning/coding |
| `llm_cpu` | `llm_generate_json` (lightweight), router role |

The optimizer does **not** change queue topology. It only changes which model is selected within the assigned queue.

---

## Adaptive Scoring Weights (from model_routing.yaml)

```
latency_weight:    0.4
throughput_weight: 0.3
error_weight:      0.2
queue_weight:      0.1
gpu_weight:        0.1
```

**Before changing weights:** run full validation sequence and verify routing behavior across all finance task categories. Document rationale.

---

## Finance-Aware Task Detection

The router detects these financial task types from request metadata:
- `earnings_analysis`, `guidance_analysis`, `capital_allocation`
- `balance_sheet_risk`, `valuation_analysis`, `peer_comparison`
- `filing_summary`, `catalyst_detection`, `rag_financial_synthesis`

Pass explicit `financial_task_type` metadata to override keyword heuristics.

---

## Semantic Complexity Classification

| Complexity | Prompt Signals |
|-----------|---------------|
| `high` | "compare capital allocation paths", "valuation sensitivity", "scenario analysis", "refinancing risk", "peer comparison", "investment thesis", "base / bull / bear", "tradeoffs", multi-filing synthesis |
| `low` | Narrow summaries, short recaps, fact extraction |
| `medium` | Everything else |

Thresholds (from `model_routing.yaml`):
- `short_prompt_chars: 400`
- `deep_prompt_chars: 3000`
- `financial_deep_analysis_chars: 2500`
- `financial_peer_compare_chars: 1800`
- `financial_rag_deep_context_chars: 5000`

---

## Finance Policy Defaults

| Task Type | Default Role | Escalation Condition |
|-----------|-------------|---------------------|
| `filing_summary` | `router` (short) / `reasoning` (medium) / `deep_reasoning` (long) | Prompt length |
| `earnings_analysis` | `reasoning` | Multi-period or multi-step |
| `guidance_analysis` | `reasoning` | Cross-period or multi-document |
| `capital_allocation` | `reasoning` | Buyback/dividend/acquisition tradeoff |
| `balance_sheet_risk` | `reasoning` | Debt-stack, refinancing, covenant, liquidity |
| `valuation_analysis` | `deep_reasoning` | Always (`valuation_force_deep_reasoning: true`) |
| `peer_comparison` | `deep_reasoning` (multi-company) / `reasoning` (narrow) | Company count |
| `catalyst_detection` | `reasoning` | Falls back to `router` under pressure |
| `rag_financial_synthesis` | `reasoning` | Large context or multi-filing → `deep_reasoning` |

---

## Pressure Fallbacks

- **GPU overload** (`gpu_overload_threshold: 95`): `valuation_analysis` + large `rag_financial_synthesis` fall back `deep_reasoning → reasoning`; `catalyst_detection` falls back to `router`.
- **Queue backlog** (`queue_backlog_threshold: 50`): same policy without changing queue topology.
- **Reasoning timeout**: retry once with `router` role on `llm_cpu`.
- **Coding timeout**: retry with `coding` role.

---

## Runtime Signals Used

- `nvidia-smi` GPU utilization
- Redis `LLEN <queue_name>` queue depth
- In-process active task counts
- Rolling per-model: `avg_latency_seconds`, `avg_tokens_per_second`, `error_rate`, `timeout_rate`
- Rolling per `(model, financial_task_type)`: same metrics
- Optional benchmark hints: `${DATA_ROOT}/reports/model_benchmark.json`

Metrics history: bounded to 1000 entries per model.
Snapshot written to: `financial-engine_v2/reports/router_metrics_snapshot.json`

---

## Invariants

- No DB schema changes required for routing.
- Celery queues (`ingest`, `embed`, `score`, `llm_gpu`, `llm_cpu`) never change.
- Embedding writes still use the vector-store contract in `06_embeddings_and_vector_store.md`.
- API and pipeline entrypoints keep their external contract; model choice is internal to the routed LLM facade.
- If telemetry is unavailable, router falls back to configured role map (no crash).

---

## What NOT to Do

- Do not change Celery queue names.
- Do not add new providers or queues in the optimizer — it only scores already-configured roles.
- Do not change adaptive weights without full validation and documented rationale.
- Do not hardcode model names in API routes or pipeline scripts — always route through `llm.py`.
- Do not fabricate benchmark scores or latency improvements.
