# Model routing

This document defines the backend model-routing layer for `financial-engine_v2`.

## Source of truth

- Routing config: `financial-engine_v2/backend/app/config/model_routing.yaml`
- Router entrypoint: `financial-engine_v2/backend/app/services/router.py`
- Runtime metrics store: `financial-engine_v2/backend/app/services/router_metrics.py`
- Runtime state collector: `financial-engine_v2/backend/app/services/router_state.py`
- Optimizer: `financial-engine_v2/backend/app/services/router_optimizer.py`
- Routed LLM facade: `financial-engine_v2/backend/app/services/llm.py`
- Optional benchmark writer: `financial-engine_v2/scripts/benchmark_models.py`
- Benchmark hint artifact: `${DATA_ROOT}/reports/model_benchmark.json` resolved from `settings.data_root`

## Role split

The backend uses five logical roles:

- `router_model`: lightweight classification and short reasoning fallback; default queue `llm_cpu`
- `coding_model`: repository/code/patch-oriented prompts; default queue `llm_gpu`
- `reasoning_model`: standard financial analysis, RAG synthesis, document extraction, and research prompts; default queue `llm_gpu`
- `deep_reasoning_model`: long-form or explicitly deep analysis prompts; default queue `llm_gpu`
- `embedding_model`: all embedding work; queue `embed`

The checked-in local routing config currently sets:

- `router_model: llama3.1:8b`
- `coding_model: llama3.1:8b`
- `reasoning_model: llama3.1:8b`
- `deep_reasoning_model: llama3.1:8b`
- `embedding_model: nomic-embed-text`

The checked-in local profile points every role at `http://127.0.0.1:11434`. The router still has internal fallback defaults in code, but operational changes should be made in `model_routing.yaml`.

## Provider split

- `coding_model`, `router_model`, `reasoning_model`, and `deep_reasoning_model` use the configured OpenAI-compatible HTTP runtime from `model_routing.yaml`
- `embedding_model` is resolved independently by the embedding facade; the checked-in local profile uses `nomic-embed-text` and an HTTP embedding runtime at `http://127.0.0.1:11434`

## Queue topology

The adaptive upgrade does not change Celery queues:

- `ingest`: discovery/download orchestration tasks
- `embed`: embedding-only jobs
- `score`: deterministic scoring jobs
- `llm_gpu`: GPU-bound coding/reasoning jobs
- `llm_cpu`: lightweight routing/classification jobs

Concrete task routing remains:

- `backfill_ticker` -> `ingest`
- `download_pdf` -> `ingest`
- `process_document` -> `llm_gpu`
- `llm_embed_texts` -> `embed`
- `llm_generate_json` -> `llm_cpu` or `llm_gpu` from `route_request(...)`

## Self-optimizing routing

The router is now finance-aware as well as adaptive:

1. Classify the request into `router`, `coding`, `reasoning`, or `embedding`.
2. Detect explicit `financial_task_type` when the request matches one of:
   - `earnings_analysis`
   - `guidance_analysis`
   - `capital_allocation`
   - `balance_sheet_risk`
   - `valuation_analysis`
   - `peer_comparison`
   - `filing_summary`
   - `catalyst_detection`
   - `rag_financial_synthesis`
3. Prefer explicit metadata over keyword heuristics. Supported additive hints include `financial_task_type`, `analysis_type`, `deep_reasoning`, `retrieved_context_chars`, `document_count`, `ticker`, `document_type`, and `source_type`.
4. Detect semantic complexity before scoring:
   - prompts containing `compare capital allocation paths`, `valuation sensitivity`, `scenario analysis`, `refinancing risk`, `peer comparison`, `investment thesis`, `base / bull / bear`, `tradeoffs`, or multi-filing synthesis cues classify as `high`
   - narrow summaries, short recaps, and fact extraction prompts classify as `low`
   - everything else classifies as `medium`
5. Collect runtime state from in-process counters, Redis queue depth, GPU telemetry, and rolling per-model plus per-model-task summaries.
6. Score the configured candidates with live metrics plus optional benchmark hints from `${DATA_ROOT}/reports/model_benchmark.json`.
7. Select the best configured model and queue without changing Celery queue names.
8. Record the result back into the rolling metrics store so the next routing decision uses updated finance-task feedback.

Classification rules remain backward-compatible:

- Requests with repo paths, code blocks, diffs, or patch instructions classify as `coding`
- Requests with financial analysis, RAG, research, or document-synthesis hints classify as `reasoning`
- Short route/classify prompts classify as `router`
- Explicit embedding requests classify as `embedding`

Broad metadata (`task_type`, `request_type`, `operation`, `intent`) still overrides the broad task classification. Finance metadata then refines the reasoning policy without changing the external API contract.

## Runtime signals

The optimizer uses the following signals:

- GPU utilization from `nvidia-smi` when available
- Redis queue depth via `LLEN queue_name`
- in-process active task counts by queue
- rolling per-model `avg_latency_seconds`
- rolling per-model `avg_tokens_per_second`
- rolling per-model `error_rate`
- rolling per-model `timeout_rate`
- rolling per `(model, financial_task_type)` `avg_latency_seconds`
- rolling per `(model, financial_task_type)` `avg_tokens_per_second`
- rolling per `(model, financial_task_type)` `error_rate`
- rolling per `(model, financial_task_type)` `timeout_rate`
- prompt length
- semantic complexity (`low`, `medium`, `high`)
- explicit `deep_reasoning` metadata override
- explicit finance hints such as `retrieved_context_chars` and `document_count`
- optional benchmark hints from `${DATA_ROOT}/reports/model_benchmark.json`

Live metrics are collected in memory. Each model keeps a bounded history (default `1000` entries) with:

- `model_name`
- `task_type`
- `latency_seconds`
- `tokens_generated`
- `tokens_per_second`
- `queue_name`
- `gpu_utilization`
- `prompt_length`
- `model_confidence`
- `queue_depth_at_dispatch`
- `timestamp`
- `success`
- `failure_reason`

The metrics layer stores rolling per-model summaries and rolling per `(model, financial_task_type)` summaries with:

- `avg_latency_seconds`
- `avg_tokens_generated`
- `avg_tokens_per_second`
- `avg_queue_depth_at_dispatch`
- `error_rate`
- `timeout_rate`

Periodic summary snapshots are also written to `financial-engine_v2/reports/router_metrics_snapshot.json`. Older snapshots without finance-task fields still load safely and fall back to global per-model summaries.

## Adaptive weights

`model_routing.yaml` now exposes the active policy weights:

- `adaptive_routing: true`
- `router_strategy: adaptive`
- `latency_weight: 0.4`
- `throughput_weight: 0.3`
- `error_weight: 0.2`
- `queue_weight: 0.1`
- `gpu_weight: 0.1`
- `queue_backlog_threshold: 50`
- `gpu_overload_threshold: 95`
- `short_prompt_chars: 400`
- `deep_prompt_chars: 3000`
- `financial_short_summary_chars: 400`
- `financial_deep_analysis_chars: 2500`
- `financial_peer_compare_chars: 1800`
- `financial_rag_deep_context_chars: 5000`
- `valuation_force_deep_reasoning: true`

## Model scoring

The model score is a weighted sum of:

- `latency_score`
- `throughput_score`
- `error_rate_score`
- `queue_pressure_score`
- `gpu_pressure_score`

## Finance policy

Default finance-aware policy:

- `filing_summary`: short summaries prefer the `router` role, medium summaries prefer the `reasoning` role, and long or explicitly deep summary requests escalate to the `deep_reasoning` role
- `earnings_analysis`: default `reasoning`; escalate for multi-period or multi-step analysis
- `guidance_analysis`: default `reasoning`; escalate for cross-period or multi-document reasoning
- `capital_allocation`: default `reasoning`; escalate for buyback/dividend/acquisition tradeoff analysis
- `balance_sheet_risk`: default `reasoning`; escalate for debt-stack, refinancing, covenant, or liquidity-heavy analysis
- `valuation_analysis`: default `deep_reasoning` when `valuation_force_deep_reasoning=true`
- `peer_comparison`: multi-company comparison prefers `deep_reasoning`; narrow relative comparisons stay on `reasoning`
- `catalyst_detection`: default `reasoning`; can fall back to `router` under pressure
- `rag_financial_synthesis`: default `reasoning`; escalate to `deep_reasoning` for large retrieved context or multi-filing synthesis

## Optimizer rules

The optimizer only scores already-configured roles. It does not invent new providers or queues.

- Short reasoning prompts route to the configured `router` role on `llm_cpu`.
- Normal reasoning prompts route to the configured `reasoning` role on `llm_gpu`.
- Deep analysis routes to the configured `deep_reasoning` role on `llm_gpu` and is marked `deferred` when the selected candidate is still a deep-reasoning role.
- Coding stays on the configured `coding` role via `llm_gpu`; when GPU pressure is high it is marked `deferred` rather than moved to a new queue.
- Embedding stays on the configured `embedding` role via `embed`.
- If GPU utilization is at or above `gpu_overload_threshold`, finance-aware fallbacks are category-specific:
  - `valuation_analysis` and large `rag_financial_synthesis` requests can fall back from `deep_reasoning` to `reasoning`
  - `catalyst_detection` and lightweight finance reasoning can fall back to `router`
- If `llm_gpu` queue depth reaches `queue_backlog_threshold`, the same pressure policy applies without changing queue topology.
- High rolling latency, elevated error rate, low throughput, benchmark hints, and finance-task-specific degradation adjust candidate scores and confidence without changing queue topology.
- If a reasoning request times out at generation time, the facade retries once with the configured `router` role on `llm_cpu`.
- If a coding request times out after dynamic routing, the facade retries with the configured `coding` role.

If runtime telemetry is unavailable, the router still functions and falls back to the configured role map.

## Benchmark file

`financial-engine_v2/scripts/benchmark_models.py` now defaults to `${DATA_ROOT}/reports/model_benchmark.json`, where `DATA_ROOT` resolves from `settings.data_root`.

The optimizer will read that file when present and use it only as a hint when live in-memory metrics are absent.

## Invariants

- No database schema changes are required for routing
- Celery queues remain `ingest`, `embed`, `score`, `llm_gpu`, and `llm_cpu`
- Embedding writes still use the governed backend vector-store contract in `06_embeddings_and_vector_store.md`
- API endpoints and pipeline entrypoints keep their existing external contract; model choice remains centralized behind the routed LLM facade
