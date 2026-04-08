# Architecture Overview

## .
**balance_sheet_forensic_analysis.py**: Forensic diagnostics for section-level metric coverage gaps.
**run.py**: Root single-command launcher for the current system.

## .claude/hooks
**start_memory_check.py**: SessionStart hook: surface relevant memories and flag stale ones.
**stop_memory_reminder.py**: Stop hook: remind Claude to save session memories.

## .claude/monitors
**bug_web_ui.py**: Bug Monitor Web UI
**extraction_workbench.py**: Extraction Workbench — backend logic for interactive extraction testing.
**monitor_agents.py**: Persistent code-change monitoring agents.

## .claude/monitors/tests
**__init__.py**: (no docstring)
**test_bug_web_ui.py**: (no docstring)

## autodev
**__init__.py**: Safe autonomous development system package.

## autodev/dashboard
**__init__.py**: Read-only AutoDev dashboard package.
**server.py**: Read-only AutoDev dashboard API and static UI server.

## autodev/runtime
**__init__.py**: Runtime modules for the autodev loop.
**autodev_loop.py**: Autonomous development loop entrypoint.
**benchmark_runner.py**: Sandbox-safe benchmark execution helpers.
**config.py**: Configuration loading for autodev runtime.
**control.py**: Safe control CLI for autodev orchestration.
**debate.py**: Deterministic debate layer with proposer, skeptic, and auditor roles.
**experiment_engine.py**: Experiment orchestration for candidate patch benchmarking.
**gates.py**: Deterministic gate execution and milestone DoD enforcement.
**native_manager.py**: Native Tenn manager runtime for OpenClaw-driven analyze/fix/verify flows.
**patch_debate.py**: Prompt helpers for proposer/skeptic/auditor patch debate.
**pr_ops.py**: PR operations with GitHub and local patch fallback.
**regression_guard.py**: Regression guard for baseline-protected metrics.
**repo_ops.py**: Git repository operations with safety checks.
**repo_rag.py**: Lightweight repository RAG indexing/search utilities.
**sandbox_runner.py**: Sandboxed command execution with allowlists and logging.
**task_discovery.py**: Deterministic repository scan to propose AutoDev tasks.
**task_queue.py**: Task and milestone parsing for autodev.
**task_scoring.py**: Task scoring and deterministic prioritization for discovery output.
**worker_interface.py**: Worker layer contracts and dispatch utilities.

## autodev/runtime/workers
**__init__.py**: Built-in worker implementations.
**llm_patch_worker.py**: LLM-based patch worker using file edits and git-generated diffs.
**local_patch_worker.py**: Deterministic local worker with safe default edit scope.

## autodev/tests
**test_autodev_placeholder.py**: (no docstring)
**test_benchmark_runner.py**: (no docstring)
**test_control_cli.py**: (no docstring)
**test_dashboard_api.py**: (no docstring)
**test_debate_layer.py**: (no docstring)
**test_experiment_engine.py**: (no docstring)
**test_llm_patch_worker.py**: (no docstring)
**test_local_codex_agent.py**: (no docstring)
**test_loop_demo_placeholder.py**: (no docstring)
**test_openclaw_runtime_recover.py**: (no docstring)
**test_openclaw_sync_openai_auth.py**: (no docstring)
**test_patch_debate.py**: (no docstring)
**test_regression_guard.py**: (no docstring)
**test_repo_rag.py**: (no docstring)
**test_task_discovery.py**: (no docstring)
**test_task_queue_user_tasks.py**: (no docstring)
**test_task_scoring.py**: (no docstring)
**test_worker_integration.py**: (no docstring)
**test_worker_interface.py**: (no docstring)

## financial-engine_v2
**orchestrator_v1.py**: (no docstring)
**run.py**: One-command production runner.

## financial-engine_v2/backend
**setup.py**: (no docstring)

## financial-engine_v2/backend/app
**__init__.py**: (no docstring)
**celery_app.py**: (no docstring)
**main.py**: (no docstring)
**worker_tasks.py**: (no docstring)

## financial-engine_v2/backend/app/alembic
**env.py**: (no docstring)

## financial-engine_v2/backend/app/alembic/versions
**0001_init.py**: (no docstring)
**0002_documents_source_url_unique.py**: (no docstring)
**0003_openbb_staging_snapshots.py**: (no docstring)
**0004_periodic_financials_period_start_currency.py**: Add period_start and currency to asx_periodic_financials.
**0005_add_total_equity_interest_expense.py**: Add total_equity and interest_expense to asx_periodic_financials.
**0006_add_announcement_type.py**: Add announcement_type to documents table.
**0007_add_companies_table.py**: Add companies master table for listed company metadata.

## financial-engine_v2/backend/app/api
**__init__.py**: (no docstring)
**analysis.py**: analysis.py — API routes for the 7-module analysis system.
**commentary.py**: commentary.py — Backend-authoritative commentary/transcript review endpoints.
**context.py**: context.py — Backend-authoritative context endpoints.
**routes.py**: (no docstring)

## financial-engine_v2/backend/app/config
**__init__.py**: (no docstring)

## financial-engine_v2/backend/app/core
**__init__.py**: (no docstring)
**config.py**: (no docstring)
**db.py**: (no docstring)

## financial-engine_v2/backend/app/models
**__init__.py**: (no docstring)
**asx_financials.py**: (no docstring)
**base.py**: (no docstring)
**documents.py**: (no docstring)
**extractions.py**: (no docstring)
**openbb_snapshots.py**: (no docstring)

## financial-engine_v2/backend/app/modules
**__init__.py**: Analysis modules — Phase 3 of the Analyse Company pipeline.
**artifacts.py**: artifacts.py — Artifact writer for analysis modules.
**balance_sheet.py**: balance_sheet.py — D1-only balance sheet analysis module.
**base.py**: base.py — Analysis module contract.
**catalysts.py**: catalysts.py — Hybrid D1+D2 catalyst identification module.
**context_loader.py**: context_loader.py — Bridge between DB/RAG/price systems and frozen TickerContext.
**math_utils.py**: math_utils.py — Null-safe financial math utilities.
**moat.py**: moat.py — Hybrid D1+D2 moat analysis module.
**orchestrator.py**: orchestrator.py — Run all analysis modules for a ticker.
**risk.py**: risk.py — Hybrid D1+D2 risk analysis module.
**roic.py**: roic.py — Return on Invested Capital analysis module.
**sentiment.py**: sentiment.py — Lightweight sentiment scoring module.
**ticker_context.py**: ticker_context.py — Typed, frozen context for analysis modules.
**valuation.py**: valuation.py — Valuation multiples and signals (D1 only, no LLM).
**watchlist_scanner.py**: watchlist_scanner.py — Scan analysis artifacts and generate alerts.

## financial-engine_v2/backend/app/modules/portfolio
**__init__.py**: Portfolio module — Phase 4 of the Analyse Company pipeline.
**analyser.py**: analyser.py — Portfolio analysis orchestrator.
**catalyst_calendar.py**: catalyst_calendar.py — Portfolio-level catalyst timeline.
**moat_quality.py**: moat_quality.py — Portfolio-level moat quality aggregation.
**position_sizing.py**: position_sizing.py — Risk-parity position sizing with quality overlay.
**reader.py**: reader.py — Load and save portfolio definitions from/to JSON.
**risk_aggregation.py**: risk_aggregation.py — Portfolio-level risk aggregation.
**types.py**: types.py — Frozen dataclasses for portfolio definitions.
**valuation_summary.py**: valuation_summary.py — Portfolio-level valuation aggregation.
**weights.py**: weights.py — Portfolio weight computation.

## financial-engine_v2/backend/app/providers
**__init__.py**: (no docstring)
**asx_provider.py**: (no docstring)
**market_price_provider.py**: (no docstring)
**marketindex_provider.py**: (no docstring)
**openbb_sidecar_provider.py**: (no docstring)
**universe.py**: Universe provider — returns the set of active tickers for a given exchange.

## financial-engine_v2/backend/app/routes
**__init__.py**: (no docstring)
**chat.py**: (no docstring)
**cockpit_api.py**: (no docstring)
**research.py**: Research endpoints — synthesis of gathered research sources.

## financial-engine_v2/backend/app/services
**__init__.py**: (no docstring)
**analysis_rag_adapter.py**: analysis_rag_adapter.py — Thin adapter between analysis modules and Qdrant.
**analysis_report_schema.py**: (no docstring)
**announcement_importance.py**: (no docstring)
**asx.py**: (no docstring)
**channel_registry.py**: (no docstring)
**cockpit_service.py**: (no docstring)
**commentary_decay.py**: (no docstring)
**commentary_ingest.py**: (no docstring)
**commentary_memo_extractor.py**: (no docstring)
**docling_extract.py**: docling_extract.py — Structured PDF extraction with table preservation and caching.
**embeddings.py**: (no docstring)
**framework_classifier.py**: (no docstring)
**framework_retriever.py**: (no docstring)
**hybrid_retriever.py**: (no docstring)
**llamacpp_embeddings.py**: (no docstring)
**llamacpp_runtime.py**: (no docstring)
**llm.py**: (no docstring)
**marketindex_headed_recovery.py**: (no docstring)
**multipass_extraction.py**: multipass_extraction.py — 4-pass financial metric extraction pipeline.
**news_memo_extractor.py**: (no docstring)
**ollama.py**: (no docstring)
**openbb_staging.py**: (no docstring)
**pipeline.py**: (no docstring)
**pipeline_service.py**: (no docstring)
**rag.py**: (no docstring)
**reranker.py**: (no docstring)
**research_context_builder.py**: (no docstring)
**research_synthesis.py**: Research synthesis service — LLM-based synthesis of gathered research sources.
**retrieval_orchestrator.py**: (no docstring)
**router.py**: (no docstring)
**router_metrics.py**: (no docstring)
**router_optimizer.py**: (no docstring)
**router_state.py**: (no docstring)
**session_memory.py**: (no docstring)
**source_registry.py**: (no docstring)
**source_weighting.py**: (no docstring)
**speaker_turn_detector.py**: speaker_turn_detector.py — Regex-based speaker-turn detection for transcripts.
**storage.py**: (no docstring)
**strategy_controller.py**: (no docstring)
**structured_chunking.py**: structured_chunking.py — Prose-section chunking for Qdrant embedding.
**system_analyzer.py**: (no docstring)
**tenn_chat.py**: (no docstring)
**transcript_watcher.py**: (no docstring)
**youtube_transcript_fetcher.py**: (no docstring)

## financial-engine_v2/backend/app/services/analysis
**__init__.py**: Analysis modules — deterministic, artifact-producing per-ticker analysis.
**context_assembler.py**: context_assembler.py — gather all inputs for a ticker analysis.
**financial_metrics.py**: financial_metrics.py — deterministic financial metric computation.
**periodic_snapshot_export.py**: Export deterministic JSON snapshots from `asx_periodic_financials`.
**report_generator.py**: report_generator.py — LLM-driven analysis report from assembled context.
**risk_module.py**: risk_module.py — structured risk aggregation per ticker.
**sector_comparison.py**: sector_comparison.py — sector-relative metric comparison for ASX equities.

## financial-engine_v2/backend/app/services/validation
**__init__.py**: (no docstring)
**extraction_schemas.py**: Extraction output validation schemas.

## financial-engine_v2/backend/app/tasks
**__init__.py**: Celery task modules for the backend app.
**commentary_tasks.py**: (no docstring)
**news_tasks.py**: (no docstring)

## financial-engine_v2/backend/app/utils
**__init__.py**: (no docstring)
**trading_calendar.py**: ASX trading calendar utilities using exchange_calendars XASX.

## financial-engine_v2/backend/tests
**conftest.py**: conftest.py — ensure the backend package is importable from the tests directory.
**test_analysis_modules.py**: test_analysis_modules.py — D1-only tests for all analysis modules.
**test_architecture_invariants.py**: (no docstring)
**test_backend_api_client_context.py**: Tests for BackendApiClient context + commentary methods.
**test_chat_route.py**: (no docstring)
**test_commentary_endpoints.py**: Tests for /api/commentary/transcripts/* endpoints.
**test_commentary_tasks.py**: (no docstring)
**test_context_endpoints.py**: Tests for /api/context/ticker and /api/context/verification endpoints.
**test_cursor_rule_compliance.py**: Mirror .cursor/rules/backend_architecture.md in CI.
**test_db_integrity.py**: test_db_integrity.py — structural and data integrity regression guards.
**test_docling_extract.py**: (no docstring)
**test_embeddings_local_point_id_compat.py**: (no docstring)
**test_extraction_capability_guards.py**: Extraction capability guards — regression protections for OCF/capex pipeline.
**test_extraction_eval.py**: Eval harness for multipass extraction accuracy.
**test_extraction_llm_separation.py**: Tests for extraction LLM / chat LLM separation.
**test_financial_metrics.py**: test_financial_metrics.py — regression guards for financial_metrics.py.
**test_local_api_key.py**: (no docstring)
**test_model_routing.py**: (no docstring)
**test_multipass_extraction.py**: Unit tests for the 4-pass multipass extraction pipeline.
**test_news_memo_extractor.py**: Tests for NewsMemoExtractor — schema validation, normalization, and upsert idempotency.
**test_news_retrieval_eval.py**: Evaluation harness for news pipeline regressions.
**test_news_tasks.py**: (no docstring)
**test_periodic_snapshot_export.py**: Tests for deterministic financial_snapshot_v0 export.
**test_prose_shares_extraction.py**: test_prose_shares_extraction.py — Tests for shares_outstanding prose fallback.
**test_qdrant_resolution.py**: (no docstring)
**test_rag_payload_guardrails.py**: (no docstring)
**test_research_synthesis.py**: Tests for backend research synthesis service.
**test_reset_system.py**: (no docstring)
**test_sentiment_rag_quality.py**: test_sentiment_rag_quality.py — RAG quality validation for sentiment module.
**test_sentiment_rag_wiring.py**: test_sentiment_rag_wiring.py — Tests for sentiment module RAG integration.
**test_speaker_turn_detector.py**: Tests for speaker_turn_detector — regex-based transcript speaker detection.
**test_system_analyzer.py**: (no docstring)
**test_system_capabilities.py**: (no docstring)
**test_tenn_chat_and_weighting.py**: Tests for tenn_chat helpers and source_weighting news_article configuration.

## financial-engine_v2/cockpit
**__init__.py**: Financial Engine Cockpit TUI package.
**main.py**: (no docstring)

## financial-engine_v2/cockpit/core
**__init__.py**: (no docstring)
**access_resume.py**: (no docstring)
**action_preview.py**: (no docstring)
**action_runtime_guards.py**: (no docstring)
**actions.py**: (no docstring)
**agent_loop.py**: Agentic chat loop for the cockpit.
**alerts.py**: (no docstring)
**backend_proposals.py**: (no docstring)
**backend_restart.py**: Restart the financial-engine backend uvicorn process.
**chart_args.py**: (no docstring)
**chat.py**: (no docstring)
**config.py**: (no docstring)
**conversation_commands.py**: (no docstring)
**export_utils.py**: (no docstring)
**job_runner.py**: (no docstring)
**llm_profile.py**: Map high-level cockpit LLM profiles to HybridRouter policy strings.
**plotly_html.py**: (no docstring)
**response_parser.py**: Parse structured LLM responses for the agentic chat protocol.
**session_memory.py**: (no docstring)
**snapshot.py**: (no docstring)
**sources.py**: Evidence sourcing formatter — compact footer showing provenance for analysis responses.
**strategy.py**: Strategy workshopping service — user-defined investment criteria and decisions.
**tool_call_debug.py**: Structured diagnostics for agent tool calls (cockpit agent loop).
**tool_definitions.py**: Tool definitions for the agentic chat loop.
**tool_executor.py**: Tool executor for the agentic chat loop.
**tools.py**: (no docstring)
**types.py**: (no docstring)
**update_delta.py**: (no docstring)
**update_status.py**: (no docstring)
**verification.py**: (no docstring)
**watchlist_trigger.py**: watchlist_trigger.py — Automated watchlist monitoring using strategy criteria.

## financial-engine_v2/cockpit/core/agent
**__init__.py**: (no docstring)
**anthropic_client.py**: AnthropicClient — adapter for the Anthropic Messages API.
**extraction_controller.py**: ExtractionController — validation gateway between agent tool calls and extraction pipeline.
**hybrid_router.py**: HybridRouter — single insertion point between the orchestrator and LLM execution.
**model_router.py**: Per-function model router for the cockpit agent system.
**subagents.py**: SubAgentSpawner — background asyncio agents with lifecycle management.

## financial-engine_v2/cockpit/core/agent/memory
**__init__.py**: Tiered memory system for the cockpit agent.
**compaction.py**: MemoryCompactor — session context-window management.
**search.py**: MemorySearch — optional SQLite-vec semantic search over memory files.
**store.py**: MemoryStore — tiered markdown memory for the cockpit agent.

## financial-engine_v2/cockpit/core/research
**__init__.py**: Research capabilities for the cockpit — dossier, memory, deep research.
**alerts.py**: Alert reader for watchlist scan results.
**deep_research.py**: Deep research meta-tool — multi-source research in a single call.
**dossier.py**: Company dossier service — persistent per-ticker research memory.
**reflection.py**: Reflection service — learn from strategy decision outcomes.
**risk_gate.py**: Risk gate — bull/bear/judge LLM debate before strategy decisions.
**signal_engine.py**: Signal engine — composite scoring and multi-ticker screening.
**situation_memory.py**: BM25-based situation memory for pattern matching.
**thesis.py**: Thesis tracking service — structured investment theses with evidence links.

## financial-engine_v2/cockpit/integrations
**__init__.py**: (no docstring)
**backend_api.py**: (no docstring)
**brave_search.py**: Brave Search API client with DuckDuckGo fallback.
**db_reader.py**: DbReader — narrowed to diagnostics-only.
**file_indexer.py**: (no docstring)
**hn_search.py**: Hacker News Algolia search client.
**llamacpp_client.py**: (no docstring)
**llamacpp_manager.py**: (no docstring)
**ollama_client.py**: (no docstring)
**qual_context.py**: (no docstring)
**qual_context_bootstrap.py**: (no docstring)
**transcript_review.py**: Transcript review service — approve/reject staged hot-source transcripts.
**web_fetcher.py**: (no docstring)

## financial-engine_v2/cockpit/storage
**__init__.py**: (no docstring)
**artifacts.py**: (no docstring)
**state.py**: (no docstring)

## financial-engine_v2/cockpit/tests
**__init__.py**: (no docstring)
**test_access_resume.py**: (no docstring)
**test_action_runtime_guards_router_mode.py**: (no docstring)
**test_agent_e2e.py**: End-to-end integration tests for the cockpit agent system.
**test_agent_stress.py**: Stress and edge-case tests for the agent loop, tool execution, and context management.
**test_alerts.py**: Tests for AlertReader (watchlist scan alert reader).
**test_anthropic_client.py**: Tests for AnthropicClient — Anthropic Messages API adapter.
**test_backend_proposals.py**: (no docstring)
**test_brave_search.py**: Tests for BraveSearchClient with DDG fallback.
**test_chat_exports.py**: (no docstring)
**test_chat_ticker_detection.py**: (no docstring)
**test_cockpit_chat_changes.py**: Integration tests for chat.py with HybridRouter and MemoryStore wired in.
**test_config_router_mode.py**: (no docstring)
**test_deep_research.py**: Tests for DeepResearchRunner (cockpit-side, mocked backend).
**test_dossier.py**: Tests for CompanyDossierService (JSONL-backed per-ticker research memory).
**test_extraction_controller.py**: Tests for ExtractionController — validation gateway between agent and extraction pipeline.
**test_hn_search.py**: Tests for HNSearchClient (Hacker News Algolia API).
**test_hybrid_router.py**: Tests for HybridRouter — local/API LLM routing.
**test_llamacpp_manager_router_mode.py**: (no docstring)
**test_llm_backend_readonly_format.py**: Tests for read-only LLM task formatting (pre-boot / capabilities).
**test_llm_profile.py**: Tests for cockpit.core.llm_profile and AgentLoop backend prefixes.
**test_memory_search.py**: Tests for MemorySearch — SQLite-vec semantic search.
**test_memory_store.py**: Tests for MemoryStore — markdown read/write.
**test_memory_stress.py**: Stress tests for the memory system: large files, many writes, and compaction.
**test_preboot_repair.py**: (no docstring)
**test_preboot_router_mode.py**: (no docstring)
**test_preboot_routing.py**: (no docstring)
**test_research_foundation.py**: Comprehensive tests for research foundation modules: dossier, situation memory, alerts.
**test_router_edge_cases.py**: Edge case tests for HybridRouter.
**test_signal_engine.py**: Tests for signal_engine.py (TickerScorer, ScreenRunner) and sector_comparison.py.
**test_situation_memory.py**: Tests for SituationMemory (BM25 + keyword fallback).
**test_sources.py**: Tests for SourcesFormatter — evidence provenance footer for analysis responses.
**test_strategy.py**: Tests for StrategyService — user-defined investment criteria and decisions.
**test_strategy_tools.py**: Tests for strategy tool integration — get_strategy handler and deep_research strategy injection.
**test_subagents.py**: Tests for SubAgentSpawner — background asyncio agents with GPU concurrency control.
**test_thesis_risk_reflection.py**: Comprehensive tests for the strategy decision pipeline:
**test_tool_call_debug.py**: Tests for tool_call_debug helpers.
**test_tool_executor_extraction.py**: Tests for ToolExecutor integration with ExtractionController.
**test_transcript_review.py**: Tests for the transcript staging and review gate.
**test_watchlist_trigger.py**: Tests for WatchlistTrigger orchestrator.

## financial-engine_v2/cockpit/ui
**__init__.py**: (no docstring)
**app.py**: (no docstring)
**help_modal.py**: (no docstring)
**preboot.py**: (no docstring)
**screens.py**: (no docstring)
**web.py**: CockpitWebApp — combined pre-boot + cockpit app for browser/web delivery.

## financial-engine_v2/scripts
**_run_metadata.py**: (no docstring)
**announcement_reaction_report.py**: (no docstring)
**asx_enrichment_sweep_action.py**: (no docstring)
**audit_extraction_backlog.py**: (no docstring)
**audit_ticker_financials.py**: (no docstring)
**backfill_asx20.py**: (no docstring)
**batch_analyse.py**: Batch analysis script — populate tickers with financial data.
**benchmark_models.py**: (no docstring)
**broad_extraction_test.py**: broad_extraction_test.py — Robustness test for multipass extraction across
**classify_announcement_importance.py**: (no docstring)
**classify_extraction_failures.py**: (no docstring)
**cleanup_asx_docs_payloads.py**: (no docstring)
**cleanup_legacy_importance_mirror.py**: (no docstring)
**cockpit_serve.py**: Thin serve wrapper for CockpitApp.
**cockpit_tui.py**: (no docstring)
**cockpit_web.py**: Entrypoint for the combined pre-boot + cockpit web app.
**conftest.py**: (no docstring)
**daily_asx_all_announcements_action.py**: (no docstring)
**daily_asx_marketwide_action.py**: (no docstring)
**daily_marketindex_action.py**: (no docstring)
**download_pdfs.py**: Download PDFs for all documents missing pdf_sha256. Run in tmux.
**embed_docs_to_qdrant.py**: Embed document PDFs from the database into the asx_docs Qdrant collection.
**embed_methodology_chunks.py**: Stage 3 embedding/indexing for methodology chunks.
**evaluate_rag_stability.py**: Evaluate RAG stability: run fixed test queries against POST /rag/query,
**export_financial_snapshot.py**: Write ``reports/analysis/{TICKER}/financial_snapshot_v0.json`` from Postgres/SQLite.
**extract_doc.py**: (no docstring)
**extract_investment_frameworks.py**: Stage 4 framework extraction for methodology documents.
**full_history_ticker_sync.py**: (no docstring)
**generate_weekly_intelligence_pack.py**: Generate a weekly intelligence pack from the last 7 days of documents.
**gpu_runtime_status.py**: GPU runtime status: query nvidia-smi, parse memory and processes, print summary.
**host_loopback_proxy.py**: (no docstring)
**ingest_ticker.py**: (no docstring)
**ingest_transcript.py**: (no docstring)
**inspect_extraction_provenance.py**: inspect_extraction_provenance.py — Show metric provenance for an extraction run.
**inspect_qdrant_collection.py**: Read-only inspection of a Qdrant RAG collection.
**inspect_retrieval_distribution.py**: Inspect RAG retrieval distribution: run random queries and report metrics.
**install_git_hooks.py**: (no docstring)
**log_change_impact.py**: (no docstring)
**marketindex_download_pdfs.py**: (no docstring)
**marketindex_ingest.py**: (no docstring)
**monitor_extraction.py**: Monitor extraction progress for a ticker and notify on completion.
**noop_chart.py**: noop_chart.py — no-op chart command stub.
**preprocess_investment_pdfs.py**: Stage 1+2 preprocessing for local investment PDF corpora.
**print_embedding_runtime_diagnostics.py**: (no docstring)
**probe_all_system_tickers.py**: (no docstring)
**promote_staged_commentary.py**: List, approve, or reject staged hot-source commentary chunks (staging → Qdrant).
**re_embed_docs.py**: Re-embed all documents for a ticker into Qdrant.
**rebuild_rag_qdrant_index.py**: (no docstring)
**rebuild_ticker_dataset.py**: (no docstring)
**rebuild_ticker_financials_from_docs.py**: (no docstring)
**recover_marketindex_headed.py**: (no docstring)
**refresh_codex_context.py**: (no docstring)
**rename_document_files.py**: (no docstring)
**reset_system.py**: (no docstring)
**resource_library_workflow.py**: Resource library workflow for custom-GPT style local knowledge ingestion.
**resume_pending_downloads.py**: (no docstring)
**run_analysis.py**: run_analysis.py — CLI entrypoint for per-ticker LLM analysis reports.
**run_asx_enrichment_chunked.py**: (no docstring)
**run_batch_extract.py**: Batch extract all unprocessed documents for a ticker. Run in tmux.
**run_extraction_backlog.py**: (no docstring)
**run_system_analyzer.py**: (no docstring)
**run_transcript_daemon.py**: (no docstring)
**test_access_resume_logic.py**: (no docstring)
**test_action_registry_doctor.py**: (no docstring)
**test_action_registry_smoke.py**: (no docstring)
**test_analysis_report_schema.py**: (no docstring)
**test_announcement_reaction_report.py**: (no docstring)
**test_asx_provider_observability.py**: (no docstring)
**test_celery_task_registration_smoke.py**: (no docstring)
**test_cockpit_access_request_triggers.py**: (no docstring)
**test_cockpit_action_intent_routing.py**: (no docstring)
**test_cockpit_action_runtime_guards.py**: (no docstring)
**test_cockpit_announcement_sync_offer.py**: (no docstring)
**test_cockpit_artifacts_price_state_markdown.py**: (no docstring)
**test_cockpit_backend_api_auth.py**: (no docstring)
**test_cockpit_chart_command.py**: (no docstring)
**test_cockpit_chat_status_widgets.py**: (no docstring)
**test_cockpit_chat_ticker_detection.py**: (no docstring)
**test_cockpit_conversation_commands.py**: (no docstring)
**test_cockpit_db_diag_query.py**: (no docstring)
**test_cockpit_db_reader_quality_signals.py**: (no docstring)
**test_cockpit_deep_analysis_grounding.py**: (no docstring)
**test_cockpit_execute_action_state_machine.py**: Tests for the execute_action / pending_action state machine in CockpitApp.
**test_cockpit_job_runner.py**: (no docstring)
**test_cockpit_llm_provider_config.py**: (no docstring)
**test_cockpit_llm_response_quality.py**: Unit tests for cockpit LLM response quality: prompt construction, post-processing
**test_cockpit_news_qual_context.py**: (no docstring)
**test_cockpit_plotly_html.py**: (no docstring)
**test_cockpit_preboot.py**: (no docstring)
**test_cockpit_price_history_chat.py**: (no docstring)
**test_cockpit_price_state.py**: (no docstring)
**test_cockpit_rag_dependency_policy.py**: (no docstring)
**test_cockpit_response_modes.py**: (no docstring)
**test_cockpit_status_normalization.py**: (no docstring)
**test_cockpit_tools_additional_context.py**: (no docstring)
**test_cockpit_update_delta_summary.py**: (no docstring)
**test_cockpit_verification_logic.py**: (no docstring)
**test_cockpit_watch_alerts.py**: (no docstring)
**test_cockpit_web_fetcher_quality.py**: (no docstring)
**test_commentary_pipeline.py**: (no docstring)
**test_extraction_backlog_tooling.py**: (no docstring)
**test_extraction_window_sampling.py**: (no docstring)
**test_framework_extraction.py**: (no docstring)
**test_import_smoke_runtime.py**: (no docstring)
**test_log_change_impact_cli.py**: (no docstring)
**test_market_data_mode_routing.py**: (no docstring)
**test_market_price_provider.py**: (no docstring)
**test_marketindex_headed_recovery_logic.py**: (no docstring)
**test_news_weighted_ranking.py**: (no docstring)
**test_openbb_sidecar_provider.py**: (no docstring)
**test_pipeline_service_extraction_accounting.py**: (no docstring)
**test_preprocess_investment_pdfs.py**: (no docstring)
**test_refresh_codex_context.py**: (no docstring)
**test_resume_pending_extraction_failures.py**: (no docstring)
**test_retrieval_pipeline.py**: (no docstring)
**test_streaming_llm_client_errors.py**: (no docstring)
**test_ticker_identity_hardening.py**: (no docstring)
**test_transcript_watcher.py**: (no docstring)
**test_update_ticker_financials_quality_gate.py**: (no docstring)
**test_worker_wrapper_parity.py**: (no docstring)
**ticker_quarantine.py**: Ticker quarantine: exclude likely non-ASX tickers from universe runs.
**update_ticker_financials.py**: (no docstring)
**validate_analysis_report.py**: (no docstring)
**validate_ticker.py**: (no docstring)
**verify_fixture_metrics.py**: Verify financial metrics from ASX PDFs using Claude API (PDF vision).
**verify_vector_baseline.py**: Verify current Qdrant vector count against the baseline written by rebuild_rag_qdrant_index.

## financial-engine_v2/scripts/archive/20260319_131047
**orchestrator_v1.py**: (no docstring)

## financial-engine_v2/worker/app
**__init__.py**: (no docstring)
**celery_app.py**: (no docstring)
**tasks.py**: (no docstring)

## financial-engine_v2/worker/worker_app
**celery_app.py**: (no docstring)
**news_tasks.py**: Celery tasks for the news ingestion pipeline.
**research_tasks.py**: Background research tasks — watchlist scanner.

## integrations/newspaper4k_au
**collect_au_finance_news.py**: (no docstring)
**playwright_fallback.py**: JS-rendering fallback for sites that newspaper4k cannot extract.
**test_collect_au_finance_news.py**: (no docstring)

## openclaw
**agent.py**: Thin OpenClaw-style control agent for AutoDev.
**codex_memory.py**: (no docstring)
**nl_router.py**: Natural-language router for OpenClaw commands with strict LLM gating.
**task_generator.py**: Create and append safe user-authored tasks for AutoDev.
**tenn_mcp_server.py**: (no docstring)

## openclaw/tests
**test_nl_router.py**: (no docstring)
**test_task_generator.py**: (no docstring)
**test_tenn_mcp_server.py**: (no docstring)

## scripts
**analyze_docling_fallbacks.py**: (no docstring)
**archive_news_urls.py**: (no docstring)
**audit_financial_metric_quality.py**: (no docstring)
**audit_news_context_db.py**: Post-index audit for news context corpus quality.
**auto_retrain_eval_loop.py**: (no docstring)
**backfill_article_relevance.py**: Backfill article_relevance rows from existing entity_links without re-fetching.
**backfill_missing_universe_announcements.py**: (no docstring)
**backfill_news.py**: (no docstring)
**benchmark_pdf_extraction.py**: (no docstring)
**bootstrap_gold_templates.py**: Bootstrap gold template files from canonical extraction output.
**build_asx_identity_map_from_filings.py**: Build an ASX ticker identity map from local filings and structured extraction data.
**build_news_chunks.py**: (no docstring)
**build_news_context_db.py**: Experimental news corpus builder for qualitative context retrieval.
**build_news_sentiment_features.py**: Build advisory-only news sentiment features from the news context SQLite DB.
**build_pdf_metric_review_set.py**: (no docstring)
**build_qualitative_context_db.py**: (no docstring)
**cashflow_layout_adapter.py**: Section-scoped cash flow layout adapter.
**cashflow_table_fallback.py**: Camelot lattice fallback for cashflow table row recovery.
**change_review_agents.py**: (no docstring)
**check_architecture_checksum.py**: Check that key architecture docs have not changed without review.
**check_canonical_regression.py**: (no docstring)
**check_environment.py**: (no docstring)
**claude_llamacpp_proxy.py**: (no docstring)
**compare_29m_to_reference.py**: Output 29M extracted metrics in the same quarter grid as the reference (Website) for accuracy comparison.
**compare_asx_coverage.py**: Compare ASX coverage metrics between baseline and optimized quantification runs.
**compare_docling_accuracy.py**: Run financial metrics extraction with both pdftotext and Docling on the same companies,
**derived_metrics.py**: (no docstring)
**detect_news_context_drift.py**: Drift detection harness for the canonical news context DB.
**docling_export_tables.py**: Quick Docling PoC: extract tables from a financial PDF and export them.
**document_classifier.py**: (no docstring)
**eval_context_retrieval.py**: (no docstring)
**export_canonical_metric_evidence_pack.py**: Export canonical metric-period rows with source screenshots for review.
**export_pdf_metric_training_jsonl.py**: (no docstring)
**extract_financial_metrics.py**: (no docstring)
**extract_pass_orchestrator.py**: Deterministic pass orchestrator for extraction candidates.
**extractor_fallback_policy.py**: Docling-first fallback policy for table extraction.
**fetch_daily_news.py**: (no docstring)
**fetch_gdelt_doc_api.py**: Fetch GDELT DOC API articles and emit local JSONL compatible with
**financial_consistency_engine.py**: Cross-metric accounting consistency checks for extracted rows.
**financial_identity_resolver.py**: (no docstring)
**financial_normalization.py**: Shared helpers for deterministic financial value normalization.
**generate_engine_health_snapshot.py**: Generate a unified daily health snapshot for the local-first research engine.
**generate_ground_truth.py**: (no docstring)
**gold_lint.py**: Lint gold label files for schema and quality constraints.
**health_guard.py**: Health gate utilities for heavyweight ingestion/extraction jobs.
**ingest_asx_rss_headlines.py**: Ingest ASX-focused RSS/Atom headlines into JSONL rows compatible with build_news_context_db.py.
**load_news_to_qdrant.py**: Sync news chunks from SQLite to Qdrant collection `news_chunks`.
**local_codex_agent.py**: (no docstring)
**local_coding_router.py**: Route coding prompts to local models by workload tier.
**metric_coverage_report.py**: (no docstring)
**metric_ontology_mapper.py**: Canonical metric alias mapping helpers for financial extraction.
**ocr_last_resort.py**: OCR last-resort helpers with fail-closed behavior.
**openclaw_runtime_recover.py**: (no docstring)
**openclaw_sync_openai_auth_from_1password.py**: (no docstring)
**parse-claude-usage.py**: (no docstring)
**pdf_rag.py**: (no docstring)
**period_ontology_mapper.py**: Canonical period-label normalization helpers for financial extraction.
**probe_news_coverage.py**: (no docstring)
**probe_news_provider_coverage.py**: (no docstring)
**protected_data_guard.py**: (no docstring)
**provenance_contract.py**: Provenance and candidate-contract utilities for extraction orchestration.
**quantify_asx_news_coverage.py**: Quantify ASX headline/media coverage from a local context_chunks SQLite corpus.
**quantify_asx_news_identity_coverage.py**: Quantify ASX news coverage using identity-aware ticker validation.
**query_financial_metrics.py**: Query extracted financial metrics for a ticker with deterministic, variant-safe selection.
**reconcile_user_table_vs_evidence.py**: Reconcile user-provided metric-period table rows against extracted evidence rows.
**report_financial_metrics_source_modes.py**: Summarise financial metric coverage by source_mode from canonical JSON.
**report_news_coverage.py**: (no docstring)
**reset_system.py**: (no docstring)
**review_pdf_metric_terminal.py**: (no docstring)
**risk_signals.py**: (no docstring)
**run_asx_headline_coverage_eval.py**: Run identity-aware ASX coverage evaluation for baseline and RSS corpora.
**run_batch_benchmark.py**: (no docstring)
**run_calibration.py**: (no docstring)
**run_extract_broad_tickers.py**: Run extract_financial_metrics on multiple ticker PDF dirs and summarize.
**run_full_pipeline.py**: (no docstring)
**run_news_pipeline.py**: Main news pipeline orchestrator.
**run_parallel_extraction.py**: (no docstring)
**run_routed_extraction.py**: (no docstring)
**run_ticker_expansion_batch.py**: Incremental ticker expansion workflow for financial metric hardening.
**runtime_python.py**: (no docstring)
**save-chat.py**: Export the current Claude Code session to a readable text file for orchestrator use.
**score_gold_run_matrix.py**: Aggregate per-ticker gold scorecards into one acceptance report.
**score_gold_set.py**: Score canonical extraction output against a per-document gold set.
**section_capture_layer.py**: Section-aware capture reinforcement layer.
**snapshot_canonical_baseline.py**: (no docstring)
**statement_classifier.py**: (no docstring)
**summarize_pdf_metric_labels.py**: (no docstring)
**sweep_stale_news_runs.py**: (no docstring)
**table_scope_classifier.py**: (no docstring)
**table_structure_reconciliation.py**: Small table-shape repairs for extracted financial tables.
**test_analyze_docling_fallbacks.py**: (no docstring)
**test_asx_coverage_quantification.py**: (no docstring)
**test_asx_optimised_ingestion.py**: (no docstring)
**test_audit_financial_metric_quality.py**: (no docstring)
**test_audit_news_context_db.py**: (no docstring)
**test_backfill_missing_universe_announcements.py**: (no docstring)
**test_balance_sheet_forensic_analysis.py**: (no docstring)
**test_bootstrap_gold_templates.py**: (no docstring)
**test_build_asx_identity_map_from_filings.py**: (no docstring)
**test_build_news_context_db.py**: (no docstring)
**test_build_news_context_db_rss_mode.py**: (no docstring)
**test_build_news_sentiment_features.py**: (no docstring)
**test_build_qualitative_context_db.py**: (no docstring)
**test_capital_structure_enhancement.py**: (no docstring)
**test_cashflow_continuation_indexing.py**: (no docstring)
**test_cashflow_cross_block_xy_pairing.py**: (no docstring)
**test_cashflow_horizontal_reconstruction.py**: (no docstring)
**test_cashflow_layout_adapter.py**: (no docstring)
**test_cashflow_pre_scope_audit.py**: (no docstring)
**test_cashflow_table_fallback.py**: (no docstring)
**test_cashflow_unmapped_emission_and_mapping.py**: (no docstring)
**test_change_review_agents.py**: (no docstring)
**test_claude_llamacpp_proxy.py**: (no docstring)
**test_cockpit_launcher_helpers.py**: (no docstring)
**test_cockpit_playwright.py**: Playwright smoke test for the Cockpit TUI served via `textual serve`.
**test_compare_docling_accuracy.py**: (no docstring)
**test_derived_metrics.py**: (no docstring)
**test_detect_news_context_drift.py**: Unit tests for news context drift detection (baseline vs actual).
**test_document_classifier.py**: (no docstring)
**test_extract_pass_orchestrator.py**: (no docstring)
**test_extractor_fallback_policy.py**: (no docstring)
**test_fallback_policy.py**: (no docstring)
**test_fetch_gdelt_doc_api.py**: (no docstring)
**test_financial_consistency_engine.py**: (no docstring)
**test_financial_identity_resolver.py**: (no docstring)
**test_financial_normalization.py**: (no docstring)
**test_generate_engine_health_snapshot.py**: (no docstring)
**test_gold_lint.py**: (no docstring)
**test_health_guard.py**: (no docstring)
**test_ingest_asx_rss_headlines.py**: (no docstring)
**test_llama_server_launchers.py**: (no docstring)
**test_load_news_qdrant_corpus_payload.py**: TDD: verify news chunk payloads include corpus='news' for Qdrant filter support.
**test_load_news_qdrant_preflight.py**: Tests for news_chunks sync preflight guards.
**test_local_coding_router.py**: (no docstring)
**test_metric_coverage_report.py**: (no docstring)
**test_metric_ontology_mapper.py**: (no docstring)
**test_news_canonical_schema.py**: Unit tests for canonical article schema (normalize + validate).
**test_news_entity_link_soft_demotion.py**: (no docstring)
**test_news_pipeline_entity_linker.py**: (no docstring)
**test_news_pipeline_providers.py**: (no docstring)
**test_news_pipeline_relevance.py**: (no docstring)
**test_news_pipeline_reporting.py**: (no docstring)
**test_news_pipeline_store.py**: (no docstring)
**test_news_pipeline_utils.py**: (no docstring)
**test_news_pipeline_workflows.py**: (no docstring)
**test_no_hallucination.py**: (no docstring)
**test_ocr_last_resort.py**: (no docstring)
**test_parallel_extraction.py**: (no docstring)
**test_pdf_financial_tools.py**: (no docstring)
**test_pdf_rag_company_validation.py**: (no docstring)
**test_period_normalization_fiscal_labels.py**: (no docstring)
**test_period_ontology_mapper.py**: (no docstring)
**test_pipeline_observability.py**: (no docstring)
**test_primary_metric_selection.py**: (no docstring)
**test_probe_news_provider_coverage.py**: (no docstring)
**test_provenance_contract.py**: (no docstring)
**test_quantify_asx_news_identity_coverage.py**: (no docstring)
**test_risk_signals.py**: (no docstring)
**test_run_asx_headline_coverage_eval.py**: (no docstring)
**test_run_extract_broad_tickers.py**: Unit tests for run_extract_broad_tickers validation and logical-doc grouping.
**test_run_news_pipeline.py**: (no docstring)
**test_run_ticker_expansion_batch.py**: (no docstring)
**test_run_wrapper_routing.py**: (no docstring)
**test_runtime_python.py**: (no docstring)
**test_score_gold_run_matrix.py**: (no docstring)
**test_score_gold_set.py**: (no docstring)
**test_section_capture_layer.py**: (no docstring)
**test_single_pdf_extraction.py**: (no docstring)
**test_statement_classifier.py**: (no docstring)
**test_table_scope_classifier.py**: (no docstring)
**test_table_structure_reconciliation.py**: (no docstring)
**test_tsr_table_identity.py**: (no docstring)
**test_validate_financial_coverage_gates.py**: (no docstring)
**test_validation_gates.py**: (no docstring)
**test_validation_quality_cycle.py**: (no docstring)
**validate_financial_coverage_gates.py**: Coverage gates for canonical financial metrics output.
**validate_financial_metrics_gates.py**: Validate extracted financial metrics files against hard ingestion gates.
**validate_news_jsonl_schema.py**: Validate a news JSONL file against the canonical article schema.
**validation_gates.py**: Hard validation gates and statement-level quarantine helpers.
**validation_quality_cycle.py**: Validation-only quality diagnostics for canonical/derived/risk outputs.
**verify_news_context_db.py**: Verify the canonical news context DB (reports/qual_context/news.sqlite).

## scripts/archive
**download_marketindex_pdfs_2026-02-17.py**: (no docstring)
**test_marketindex_2026-02-17.py**: (no docstring)

## scripts/archive/backup_20260217_192352
**download_marketindex_pdfs.py**: (no docstring)
**fetch.py**: (no docstring)
**fetch_asx.py**: (no docstring)
**test_marketindex.py**: (no docstring)

## scripts/archive/backup_20260217_193048
**download_marketindex_pdfs.py**: (no docstring)

## scripts/archive/backup_20260217_193315
**download_marketindex_pdfs.py**: (no docstring)

## scripts/archive/backup_20260217_194711
**test_marketindex.py**: (no docstring)

## scripts/archive/backup_20260217_200917
**download_marketindex_pdfs.py**: (no docstring)

## scripts/archive/backup_20260217_204602
**daily_marketindex_action.py**: (no docstring)
**download_marketindex_pdfs.py**: (no docstring)
**test_download_marketindex_pdfs_logic.py**: (no docstring)
**test_marketindex.py**: (no docstring)

## scripts/archive/legacy_cleanup_20260309
**archive_news_urls.py**: (no docstring)
**auto_self_train_financial_extractor.py**: (no docstring)
**test_archive_news_urls.py**: (no docstring)
**test_local_codex_agent.py**: (no docstring)
**test_news_pipeline_ingest.py**: (no docstring)

## scripts/archive/legacy_root_20260218
**classify.py**: (no docstring)
**daily_marketindex_action.py**: (no docstring)
**download_marketindex_pdfs.py**: (no docstring)
**fetch.py**: (no docstring)
**fetch_asx.py**: (no docstring)
**test_download_marketindex_pdfs_logic.py**: (no docstring)
**test_marketindex.py**: (no docstring)

## scripts/archive/system_checkpoint_20260217_212812
**daily_marketindex_action.py**: (no docstring)
**download_marketindex_pdfs.py**: (no docstring)
**fetch.py**: (no docstring)
**fetch_asx.py**: (no docstring)
**test_download_marketindex_pdfs_logic.py**: (no docstring)
**test_marketindex.py**: (no docstring)

## scripts/news_pipeline
**__init__.py**: ASX news pipeline v2 package.
**canonical_article_schema.py**: Canonical article schema for the news substrate (Layer 2).
**chunk_builder.py**: (no docstring)
**cli_common.py**: (no docstring)
**db.py**: (no docstring)
**entity_linker.py**: (no docstring)
**ingest.py**: (no docstring)
**models.py**: (no docstring)
**relevance.py**: (no docstring)
**reporting.py**: (no docstring)
**utils.py**: (no docstring)

## scripts/news_pipeline/providers
**__init__.py**: (no docstring)
**base.py**: (no docstring)
**eodhd.py**: (no docstring)
**gdelt.py**: (no docstring)
**newspaper4k.py**: Newspaper4k provider — full article scraping via collect_au_finance_news.
**rss.py**: RSS provider wrapping the existing ingest_asx_rss_headlines implementation.
**worldmonitor.py**: (no docstring)

## services/evaluation
**anomaly.py**: (no docstring)
**calibration.py**: (no docstring)
**confidence.py**: (no docstring)
**evidence.py**: (no docstring)
**evidence_utils.py**: (no docstring)
**ground_truth_loader.py**: (no docstring)
**normalizer.py**: (no docstring)
**scorer.py**: (no docstring)

## services/extraction
**docling_runner.py**: (no docstring)
**pdf_classifier.py**: (no docstring)
**router.py**: (no docstring)

## services/orchestrator
**pipeline_orchestrator.py**: (no docstring)
