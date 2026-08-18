# Child Task Proposals

These are draft follow-up cards only. No GitHub issues were created and no PR
or product files were changed by this audit.

## C01 - Architecture Invariant Reconciliation

Title: `[CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39`

Lane: Evaluation. Supporting lane: Repo Hygiene.

Allowed files:

- `docs/agent_tasks/pr39_architecture_invariant_reconciliation_v1.md`
- `reports/agent_jobs/pr39_architecture_invariant_reconciliation_v1/**`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/architecture/06_embeddings_and_vector_store.md`
- `docs/architecture/22_memory_ownership_map.md`
- Exact runtime files named by the failing invariant report only, if the
  approved child task permits code remediation.

Forbidden:

- Production DB/Qdrant/news/memory mutation.
- Canonical financial truth, parser routing, extraction prompts, gold labels.
- Runtime/model/GPU/service config.
- Relaxing architecture invariants without explicit migration approval.
- Removing documented SQLite-backed memory/operational-store ownership without
  a separate migration.

Validation:

- Focused architecture invariant pytest.
- Architecture-check against docs/architecture invariants.
- Ruff and `git diff --check`.

Hard stop: any proposed fix requires changing the architecture invariant itself
instead of making code comply.

## C02 - Cockpit Chat Controller Contract

Title: `[CI] Align Cockpit chat controller test doubles with llm_client contract`

Lane: Query Orchestration.

Allowed files:

- `docs/agent_tasks/pr39_cockpit_chat_controller_contract_v1.md`
- `reports/agent_jobs/pr39_cockpit_chat_controller_contract_v1/**`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py`
- `financial-engine_v2/backend/tests/test_cockpit_conversation_continuity.py`

Forbidden:

- Runtime/model/GPU/service config.
- Broad router rewrites.
- Test-only masking without proving `chat_stream` behavior.

Validation:

- Focused cockpit service session/thread and conversation continuity pytest.

## C03 - Cockpit Subagent Event Loop

Title: `[CI] Make Cockpit subagent event-loop contract explicit under pytest-asyncio`

Lane: Query Orchestration.

Allowed files:

- `docs/agent_tasks/pr39_cockpit_subagent_event_loop_v1.md`
- `reports/agent_jobs/pr39_cockpit_subagent_event_loop_v1/**`
- `financial-engine_v2/cockpit/core/agent/subagents.py`
- `financial-engine_v2/cockpit/tests/test_subagents.py`

Forbidden:

- Live local LLM, GPU, runtime service, or memory-store mutation.
- Broad async framework rewrite.

Validation:

- `pytest -c pytest.ini financial-engine_v2/cockpit/tests/test_subagents.py -q`

## C04 - Streaming Subprocess job_id Contract

Title: `[CI] Align streaming subprocess helper tests with required job_id`

Lane: Repo Hygiene.

Allowed files:

- `docs/agent_tasks/pr39_streaming_subprocess_job_id_contract_v1.md`
- `reports/agent_jobs/pr39_streaming_subprocess_job_id_contract_v1/**`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_streaming_subprocess.py`

Forbidden:

- Live subprocess action execution outside tests.
- Runtime/service config changes.

Validation:

- `pytest -c pytest.ini financial-engine_v2/backend/tests/test_streaming_subprocess.py -q`

## C05 - News Loader Ollama URL API

Title: `[CI] Verify or carry Ollama URL loader repair into PR #39 before rerun`

Lane: Query Orchestration.

Allowed files:

- `docs/agent_tasks/pr39_news_loader_ollama_url_contract_v1.md`
- `reports/agent_jobs/pr39_news_loader_ollama_url_contract_v1/**`
- `scripts/load_news_to_qdrant.py`
- `financial-engine_v2/backend/tests/test_load_news_to_qdrant.py`

Forbidden:

- Production news store mutation.
- Qdrant mutation.
- Live nightly sync.
- Runtime/model/GPU/service config.

Validation:

- `pytest -c pytest.ini financial-engine_v2/backend/tests/test_load_news_to_qdrant.py -q`
- Static proof no live sync/backfill ran.

Note: local HEAD `730eb0d8` appears to contain a candidate repair, but PR #39
GitHub head is still `8635833b`.

## C06 - Marketplace Time-Stable Fixtures

Title: `[CI] Stabilize marketplace benchmark fixtures against wall-clock drift`

Lane: Evaluation.

Allowed files:

- `docs/agent_tasks/pr39_marketplace_time_stable_fixtures_v1.md`
- `reports/agent_jobs/pr39_marketplace_time_stable_fixtures_v1/**`
- `financial-engine_v2/backend/app/services/marketplace_price_intelligence.py`
- `financial-engine_v2/backend/app/services/marketplace_scanner.py`
- Marketplace backend test files named in `failure_clusters.json`.

Forbidden:

- Production marketplace data.
- Canonical financial truth.
- Cosmetic expectation drift that hides stale-benchmark behavior.

Validation:

- Focused marketplace API, price intelligence, and scanner pytest.

## C07/C08 - Cockpit Grounding And Router Contract

Title: `[CI] Reconcile Cockpit stress, HybridRouter, and grounded-refusal contracts`

Lane: Query Orchestration.

Allowed files:

- `docs/agent_tasks/pr39_cockpit_router_grounding_contract_v1.md`
- `reports/agent_jobs/pr39_cockpit_router_grounding_contract_v1/**`
- `financial-engine_v2/cockpit/core/agent/agent_loop.py`
- `financial-engine_v2/cockpit/core/agent/hybrid_router.py`
- `financial-engine_v2/cockpit/tests/test_agent_stress.py`
- `financial-engine_v2/cockpit/tests/test_cockpit_chat_changes.py`
- `financial-engine_v2/cockpit/tests/test_router_edge_cases.py`

Forbidden:

- Removing or weakening financial grounding guards.
- Silent local/API fallback.
- Live tool execution.
- Runtime/model/GPU/service config.

Validation:

- Focused Cockpit agent stress, chat changes, and router edge-case pytest.

## C09 - Memo Signal Routing

Title: `[CI] Restore or re-contract memo extractor signal routing in isolated tests`

Lane: Memory.

Allowed files:

- `docs/agent_tasks/pr39_memo_signal_routing_contract_v1.md`
- `reports/agent_jobs/pr39_memo_signal_routing_contract_v1/**`
- `financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py`
- `financial-engine_v2/backend/app/services/company_memory.py`
- `financial-engine_v2/backend/app/services/memory_events.py`

Forbidden:

- Production memory, news, DB, or Qdrant mutation.
- Broad memory migration.

Validation:

- Focused memo extractor signal-routing pytest using isolated temp stores only.

## C10/C13 - Preferences And Query Sufficiency

Title: `[CI] Review Cockpit preferences response and query sufficiency contract failures`

Lane: Query Orchestration.

Allowed files:

- `docs/agent_tasks/pr39_preferences_and_query_sufficiency_v1.md`
- `reports/agent_jobs/pr39_preferences_and_query_sufficiency_v1/**`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_preferences.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/rag.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`

Forbidden:

- Canonical financial truth.
- Parser routing.
- Source-label relaxation.
- Production data mutation.

Validation:

- Focused preferences and query orchestrator pytest.

## C11 - Real-Gold PDF Asset

Title: `[CI] Resolve missing real-gold PDF asset path or fixture contract for PR #39`

Lane: Evaluation.

Allowed files:

- `docs/agent_tasks/pr39_real_gold_pdf_asset_resolution_v1.md`
- `reports/agent_jobs/pr39_real_gold_pdf_asset_resolution_v1/**`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `financial-engine_v2/data/asx/docs/10X/financial_performance/**`

Forbidden:

- Gold label mutation without provenance review.
- Parser routing and extraction prompts.
- Canonical financial truth mutation.

Validation:

- Focused extraction gold eval pytest.
- Provenance check before adding or relocating any PDF.

## C12 - Process Document Redis/Celery CI Dependency

Title: `[CI] Isolate process-document API test from live Redis or declare CI Redis service`

Lane: Repo Hygiene.

Allowed files:

- `docs/agent_tasks/pr39_process_document_api_ci_dependency_v1.md`
- `reports/agent_jobs/pr39_process_document_api_ci_dependency_v1/**`
- `financial-engine_v2/backend/tests/test_process_document_api.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/worker_tasks.py`
- `.github/workflows/ci.yml`

Forbidden:

- Production Redis/Celery, DB, Qdrant, or service mutation.
- Broad workflow/dependency changes beyond the process-document test contract.

Validation:

- Focused process-document API pytest.
- Read-only workflow review; no live worker run.
