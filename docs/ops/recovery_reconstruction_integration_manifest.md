# Recovery Reconstruction Integration Manifest

## Purpose

This manifest defines the safe integration strategy for promoting selected work from
`recovery/reconstruction` into the current operational baseline on `origin/main`.

Primary rule:
- Use `origin/main` as the preservation base.
- Do not merge `recovery/reconstruction` wholesale.
- Port recovery changes in themed batches onto `origin/main`.

## Base Decision

`origin/main` is the mainline runtime shape.

Reason:
- It contains the current compose topology, dedicated worker package, cockpit UI/config,
  ticker identity map, ops runbooks, and separate news-pipeline stack.
- `recovery/reconstruction` contains useful backend and operator improvements, but also
  introduces a competing task/runtime topology and a larger routing/runtime stack that
  should not be promoted without an explicit runtime decision.

## Must Preserve

These `origin/main` assets should not be dropped during integration:

- `/home/l4nd0/tenn/financial-engine_v2/docker-compose.yml`
- `/home/l4nd0/tenn/financial-engine_v2/worker/Dockerfile`
- `/home/l4nd0/tenn/financial-engine_v2/worker/app/celery_app.py`
- `/home/l4nd0/tenn/financial-engine_v2/worker/app/tasks.py`
- `/home/l4nd0/tenn/financial-engine_v2/worker/entrypoint.sh`
- `/home/l4nd0/tenn/financial-engine_v2/worker/requirements.txt`
- `/home/l4nd0/tenn/financial-engine_v2/worker/worker_app/__init__.py`
- `/home/l4nd0/tenn/financial-engine_v2/worker/worker_app/celery_app.py`
- `/home/l4nd0/tenn/financial-engine_v2/worker/worker_app/tasks.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/access_resume.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/action_runtime_guards.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/actions.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/alerts.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/chat.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/conversation_commands.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/tools.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/update_delta.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/core/update_status.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/backend_api.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/db_reader.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/file_indexer.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/ollama_client.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/qual_context.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/web_fetcher.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/storage/artifacts.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/storage/state.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/app.py`
- `/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/screens.py`
- `/home/l4nd0/tenn/financial-engine_v2/config/cockpit.local.yaml`
- `/home/l4nd0/tenn/financial-engine_v2/config/cockpit.yaml`
- `/home/l4nd0/tenn/financial-engine_v2/config/ticker_identity_map.json`
- `/home/l4nd0/tenn/docs/ops/01_nvml_host_stabilization_runbook.md`
- `/home/l4nd0/tenn/docs/ops/02_ollama_m40_validation_and_mitigation.md`
- `/home/l4nd0/tenn/docs/ops/03_model_tiering_m40_24gb.md`
- `/home/l4nd0/tenn/docs/ops/04_batch_pipeline_architecture_fastapi_celery.md`
- `/home/l4nd0/tenn/docs/ops/05.compose.phase1.yml`
- `/home/l4nd0/tenn/docs/ops/05_compose_phase1_host_gpu_blueprint.md`
- `/home/l4nd0/tenn/docs/ops/06_production_hardening_acceptance_suite.md`
- `/home/l4nd0/tenn/docs/ops/07_production_hardening_execution_worksheet.md`
- `/home/l4nd0/tenn/docs/ops/CHANGELOG.md`
- `/home/l4nd0/tenn/docs/ops/README.md`
- `/home/l4nd0/tenn/docs/ops/quickstart.md`
- `/home/l4nd0/tenn/scripts/news_pipeline/__init__.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/chunk_builder.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/cli_common.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/db.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/entity_linker.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/ingest.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/models.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/providers/__init__.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/providers/base.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/providers/eodhd.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/providers/gdelt.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/providers/worldmonitor.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/reporting.py`
- `/home/l4nd0/tenn/scripts/news_pipeline/utils.py`
- `/home/l4nd0/tenn/integrations/newspaper4k_au/README.md`
- `/home/l4nd0/tenn/integrations/newspaper4k_au/collect_au_finance_news.py`
- `/home/l4nd0/tenn/integrations/newspaper4k_au/requirements.txt`

Preservation rules:
- Keep the separate `financial-engine_v2/worker` execution model until an explicit
  migration replaces it.
- Keep cockpit path contracts intact.
- Keep `financial-engine_v2/docker-compose.yml` as the operational base.

## Safe To Port Now

These recovery changes are strong candidates for first-wave integration onto `origin/main`.

### Backend Guardrails

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/core/config.py`
  Adopt selectively:
  runtime env-file selection, Docker-vs-host URL normalization, Redis/Qdrant rewriting,
  project-root path normalization.

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/pipeline.py`
  Adopt selectively:
  document quarantine rule loading, payload validation, rejected-payload logging,
  `docs_root`-based path handling, and richer ingestion counters.

- `/home/l4nd0/tenn/financial-engine_v2/backend/tests/test_qdrant_resolution.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/tests/test_rag_payload_guardrails.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/tests/test_commentary_tasks.py`

### Operator Scripts

- `/home/l4nd0/tenn/financial-engine_v2/scripts/run_local_backend.sh`
  Port recovery improvements by hand. Preserve the current startup contract used by cockpit.

- `/home/l4nd0/tenn/financial-engine_v2/scripts/smoke_local.sh`
  Port recovery improvements by hand. Treat the stronger checks as an enhanced local smoke path.

- `/home/l4nd0/tenn/financial-engine_v2/scripts/full_history_ticker_sync.py`
  Port recovery improvements by hand:
  `--asx20`, `--months`, `--skip-complete`, `--min-docs-to-skip`, `--concurrency`,
  interrupt handling, health gating, and quarantine integration.

- `/home/l4nd0/tenn/financial-engine_v2/scripts/ticker_quarantine.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/reset_system.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/gpu_runtime_status.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/verify_vector_baseline.py`

### Low-Risk Supporting Files

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/providers/market_price_provider.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/text_extract.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/worker_tasks.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/setup.py`

## Defer Until Runtime Decision

These recovery assets look useful, but they should not become mainline until the runtime
policy is explicit.

### Runtime Topology Shift

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/celery_app.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/tasks/commentary_tasks.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/pipeline_service.py`

Reason:
- These changes pull task orchestration into `backend/app`, while `origin/main` still runs
  Celery from `financial-engine_v2/worker`.

### Router / LLM / Analyzer Stack

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/config/model_routing.yaml`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/llm.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/router.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/router_state.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/router_metrics.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/router_optimizer.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/system_analyzer.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/tests/test_model_routing.py`

Reason:
- This stack assumes `llama.cpp`, new routing config, analyzer feedback, and queue/runtime
  semantics that are not yet the declared ops baseline.

### Commentary / RAG / OpenBB Feature Sets

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/channel_registry.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/commentary_ingest.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/commentary_memo_extractor.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/rag.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/research_context_builder.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/source_registry.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/source_weighting.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/transcript_watcher.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/models/openbb_snapshots.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/providers/openbb_sidecar_provider.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/openbb_staging.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/run_system_analyzer.py`

Reason:
- These are coherent second-wave features, but they introduce new APIs, storage/state,
  provider expectations, or runtime dependencies and should land as themed batches.

## Manual-Merge Hotspots

These files should not be auto-merged. Review them line-by-line on an integration branch:

- `/home/l4nd0/tenn/financial-engine_v2/backend/app/api/routes.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/celery_app.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/core/config.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/ollama.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/pipeline.py`
- `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/pipeline_service.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/full_history_ticker_sync.py`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/healthcheck.sh`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/update_ticker_financials.py`

Specific handling:
- Keep `origin/main` behavior for `/home/l4nd0/tenn/financial-engine_v2/backend/app/services/ollama.py`.
- Keep `origin/main` worker/compose assumptions for `/home/l4nd0/tenn/financial-engine_v2/backend/app/api/routes.py`
  and `/home/l4nd0/tenn/financial-engine_v2/backend/app/celery_app.py`.
- Preserve the `origin/main` DB alignment fix in
  `/home/l4nd0/tenn/financial-engine_v2/scripts/update_ticker_financials.py`.
- Do not let recovery replace `/home/l4nd0/tenn/financial-engine_v2/scripts/healthcheck.sh`
  unchanged unless runtime policy explicitly moves away from the current Ollama-based baseline.

## First Execution-Safe Steps

1. Create a scratch integration branch or worktree from `origin/main`.
2. Copy this manifest into the branch context and verify all `Must Preserve` assets remain untouched.
3. Port only the `Safe To Port Now` items first.
4. Run targeted verification for each batch before moving to the next one.
5. Keep all deferred recovery work parked in branch/worktree form until the runtime policy is explicit.

## Non-Goals For First Merge

Do not include these in the first integration wave:
- backend-integrated Celery topology replacement
- router/analyzer/model-routing stack promotion
- full commentary/RAG/OpenBB promotion as one combined merge
- broad dependency expansion driven by deferred runtime features
