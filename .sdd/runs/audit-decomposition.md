# Tenn System Audit — Task Decomposition

**Goal:** Full end-to-end audit of the Tenn system across 10 scoped components.
**Created:** 2026-04-02
**Rating System:** Each component scored 1–10 on Correctness, Integration, Resilience, Efficiency, Test Coverage.

---

## Task 1: PDF Extraction Pipeline Audit

**Scope:** All passes, fallbacks, OCR paths, metric provenance.

**Files to trace:**
- `financial-engine_v2/backend/app/services/multipass_extraction.py` — core multipass orchestration
- `financial-engine_v2/backend/app/services/docling_extract.py` — Docling backend (canonical)
- `financial-engine_v2/backend/app/services/pipeline.py` — pipeline orchestration
- `financial-engine_v2/backend/app/services/pipeline_service.py` — pipeline service layer
- `financial-engine_v2/backend/app/services/llamacpp_runtime.py` — LLM runtime (JSON sanitizer)
- `financial-engine_v2/backend/app/services/framework_classifier.py` — ASX framework detection
- `financial-engine_v2/backend/app/services/marketindex_headed_recovery.py` — headed table recovery
- `financial-engine_v2/scripts/broad_extraction_test.py` — robustness test harness
- `financial-engine_v2/scripts/cashflow_layout_adapter.py` — cashflow layout
- `financial-engine_v2/scripts/cashflow_table_fallback.py` — cashflow fallback

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `pytest financial-engine_v2/backend/tests/test_extraction_eval.py`
- `pytest financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `pytest financial-engine_v2/backend/tests/test_extraction_llm_separation.py`
- `pytest financial-engine_v2/backend/tests/test_docling_extract.py`
- `pytest financial-engine_v2/backend/tests/test_prose_shares_extraction.py`

**Audit checklist:**
- [ ] Trace multipass execution: Pass 1 → Pass 2 → Pass 3 flow
- [ ] Verify Docling is default backend (not pymupdf) per project memory
- [ ] Trace OCR fallback path — when does it trigger?
- [ ] Verify JSON sanitizer strips control chars from garbled PDFs
- [ ] Check metric provenance — can every extracted number be traced to a source cell/page?
- [ ] Verify validation gate rejects missing period_end and insufficient metrics
- [ ] Check for silent failures in extraction (swallowed exceptions, default returns)
- [ ] Verify framework classifier correctly routes 4D/4E/5B/full IFRS

**Integration points to verify:**
- Extraction → DB upsert (what fields are written?)
- Extraction → Celery task dispatch (which queue?)
- LLM runtime → llama.cpp server (prompt routing, error handling)

---

## Task 2: Financial Metric Database Audit

**Scope:** Schema integrity, ingestion accuracy, deduplication.

**Files to trace:**
- `financial-engine_v2/backend/app/models/asx_financials.py` — periodic financials model
- `financial-engine_v2/backend/app/models/documents.py` — document model
- `financial-engine_v2/backend/app/models/extractions.py` — extraction model
- `financial-engine_v2/backend/app/models/companies.py` — companies model
- `financial-engine_v2/backend/app/models/openbb_snapshots.py` — market data snapshots
- `financial-engine_v2/backend/app/models/base.py` — base model
- `financial-engine_v2/backend/app/core/db.py` — DB connection setup
- `financial-engine_v2/backend/app/alembic/versions/` — all 7 migrations

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_db_integrity.py`
- `pytest financial-engine_v2/backend/tests/test_financial_metrics.py`

**Audit checklist:**
- [ ] Trace all 7 Alembic migrations in order — are they linear and non-conflicting?
- [ ] Verify unique constraints prevent duplicate metrics for same ticker+period
- [ ] Check index coverage on frequently queried columns
- [ ] Verify ingestion path: extraction result → model → DB write
- [ ] Check for orphaned records (documents without extractions, extractions without documents)
- [ ] Verify `period_start`, `period_end`, `currency` columns exist (migration 0004)
- [ ] Verify `announcement_type` column exists (migration 0006)
- [ ] Verify companies table exists and has proper constraints (migration 0007)
- [ ] Check for data type mismatches between extraction output and DB schema

**Integration points to verify:**
- Extraction pipeline → DB write path
- DB → RAG pipeline (what data feeds into vector store?)
- DB → API endpoints (what queries are used?)

---

## Task 3: RAG Pipeline Audit

**Scope:** Qdrant vector store, nomic-embed-text embeddings, hybrid retrieval.

**Files to trace:**
- `financial-engine_v2/backend/app/services/rag.py` — RAG service
- `financial-engine_v2/backend/app/services/embeddings.py` — embedding service
- `financial-engine_v2/backend/app/services/llamacpp_embeddings.py` — local embeddings via llama.cpp
- `financial-engine_v2/backend/app/services/hybrid_retriever.py` — hybrid retrieval
- `financial-engine_v2/backend/app/services/retrieval_orchestrator.py` — retrieval orchestration
- `financial-engine_v2/backend/app/services/reranker.py` — reranking
- `financial-engine_v2/backend/app/services/structured_chunking.py` — document chunking
- `financial-engine_v2/backend/app/services/source_weighting.py` — source weighting
- `financial-engine_v2/backend/app/services/source_registry.py` — source registry
- `financial-engine_v2/backend/app/services/analysis_rag_adapter.py` — analysis RAG adapter

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_qdrant_resolution.py`
- `pytest financial-engine_v2/backend/tests/test_rag_payload_guardrails.py`
- `pytest financial-engine_v2/backend/tests/test_sentiment_rag_quality.py`
- `pytest financial-engine_v2/backend/tests/test_sentiment_rag_wiring.py`
- `pytest financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py`
- `pytest financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`

**Audit checklist:**
- [ ] Verify Qdrant collection creation and schema
- [ ] Trace embedding generation: document → chunks → vectors → Qdrant upsert
- [ ] Verify nomic-embed-text is the embedding model used
- [ ] Check hybrid retrieval: dense + sparse search combination
- [ ] Verify reranking logic and scoring
- [ ] Check source weighting — how are different sources prioritized?
- [ ] Verify RAG payload guardrails prevent data leakage
- [ ] Check for stale vectors (documents updated but vectors not re-embedded)
- [ ] Verify point ID compatibility for local embeddings

**Integration points to verify:**
- DB → Embedding pipeline (what triggers re-embedding?)
- Qdrant → Chat endpoint (retrieval → prompt construction)
- Source registry → Retrieval (correct source filtering?)

---

## Task 4: News Intelligence Layer Audit

**Scope:** GDELT + EODHD ingestion, deduplication, entity linking.

**Files to trace:**
- `financial-engine_v2/backend/app/tasks/news_tasks.py` — news Celery tasks
- `financial-engine_v2/backend/app/services/news_memo_extractor.py` — news memo extraction
- `financial-engine_v2/backend/app/services/commentary_ingest.py` — commentary ingestion
- `financial-engine_v2/backend/app/services/commentary_memo_extractor.py` — commentary memo extraction
- `financial-engine_v2/backend/app/services/commentary_decay.py` — commentary decay/aging
- `financial-engine_v2/backend/app/services/announcement_importance.py` — importance scoring
- `financial-engine_v2/cockpit/integrations/qual_context.py` — qualitative context reader
- `scripts/build_news_context_db.py` — news context DB builder
- `scripts/build_news_chunks.py` — news chunking
- `scripts/build_news_sentiment_features.py` — sentiment features
- `scripts/backfill_news.py` — news backfill

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
- `pytest financial-engine_v2/backend/tests/test_news_tasks.py`
- `pytest financial-engine_v2/backend/tests/test_news_memo_extractor.py`
- `pytest financial-engine_v2/backend/tests/test_commentary_endpoints.py`
- `pytest financial-engine_v2/backend/tests/test_commentary_tasks.py`

**Audit checklist:**
- [ ] Verify newspaper4k is canonical news provider (EODHD/GDELT suspended per project memory)
- [ ] Trace news ingestion: fetch → parse → deduplicate → store
- [ ] Check deduplication logic — URL-based? Content hash?
- [ ] Verify entity linking: how are news articles linked to tickers?
- [ ] Check commentary decay — how does old news age out?
- [ ] Verify no data leakage: news data must NOT contaminate financial filings pipeline
- [ ] Check memo extraction quality — what gets extracted from articles?
- [ ] Verify importance scoring logic

**Integration points to verify:**
- News → Qdrant (separate collection? same collection with source tag?)
- News → Chat (how does news context reach the prompt?)
- News → Celery (which queue? error handling?)

---

## Task 5: Celery Task Queue Audit

**Scope:** Worker health, task routing, failure handling.

**Files to trace:**
- `financial-engine_v2/backend/app/celery_app.py` — Celery app configuration
- `financial-engine_v2/backend/app/worker_tasks.py` — worker task definitions
- `financial-engine_v2/backend/app/tasks/news_tasks.py` — news tasks
- `financial-engine_v2/backend/app/tasks/commentary_tasks.py` — commentary tasks
- `financial-engine_v2/worker/` — dedicated worker service
- `docker-compose.yml` — worker service definition (queues: ingest, embed, score, llm_cpu, llm_gpu)

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_news_tasks.py`
- `pytest financial-engine_v2/backend/tests/test_commentary_tasks.py`

**Audit checklist:**
- [ ] Verify queue definitions: ingest, embed, score, llm_cpu, llm_gpu
- [ ] Trace task routing — which tasks go to which queues?
- [ ] Check failure handling: retries, dead letter, error reporting
- [ ] Verify beat scheduler configuration (fe_beat service)
- [ ] Check for task timeout configuration
- [ ] Verify Redis broker connectivity and configuration
- [ ] Check for task result backend configuration
- [ ] Verify worker concurrency settings
- [ ] Check for task idempotency (safe to retry?)

**Integration points to verify:**
- API → Celery (which endpoints dispatch async tasks?)
- Celery → DB (task results written back correctly?)
- Celery → Qdrant (embedding tasks write to vector store?)
- Beat → Worker (scheduled tasks executing?)

---

## Task 6: FastAPI Endpoints Audit

**Scope:** Response correctness, error handling, auth.

**Files to trace:**
- `financial-engine_v2/backend/app/main.py` — FastAPI app setup
- `financial-engine_v2/backend/app/routes/chat.py` — chat routes
- `financial-engine_v2/backend/app/routes/cockpit_api.py` — cockpit API
- `financial-engine_v2/backend/app/routes/research.py` — research routes
- `financial-engine_v2/backend/app/routes/__init__.py` — route registration
- `financial-engine_v2/backend/app/services/tenn_chat.py` — chat service
- `financial-engine_v2/backend/app/config/` — app configuration

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_chat_route.py`
- `pytest financial-engine_v2/backend/tests/test_context_endpoints.py`
- `pytest financial-engine_v2/backend/tests/test_commentary_endpoints.py`
- `pytest financial-engine_v2/backend/tests/test_local_api_key.py`
- `pytest financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- `pytest financial-engine_v2/backend/tests/test_system_capabilities.py`

**Audit checklist:**
- [ ] List all registered endpoints and their HTTP methods
- [ ] Check authentication/authorization on each endpoint
- [ ] Verify error response format consistency
- [ ] Check for input validation on all request bodies
- [ ] Verify health endpoint at `/api/health`
- [ ] Check CORS configuration
- [ ] Verify rate limiting (if any)
- [ ] Check for SQL injection vectors in query parameters
- [ ] Verify response schemas match documented API

**Integration points to verify:**
- Endpoints → Services (proper dependency injection?)
- Endpoints → Celery (async task dispatch?)
- Endpoints → DB (connection pooling, session management?)

---

## Task 7: Cockpit UI Audit

**Scope:** Data accuracy displayed vs stored, broken views, missing states.

**Files to trace:**
- `financial-engine_v2/cockpit/ui/web.py` — web UI (primary entrypoint per project memory)
- `financial-engine_v2/cockpit/ui/app.py` — app setup
- `financial-engine_v2/cockpit/ui/screens.py` — screen definitions
- `financial-engine_v2/cockpit/ui/preboot.py` — preboot screen
- `financial-engine_v2/cockpit/core/chat.py` — chat logic
- `financial-engine_v2/cockpit/core/agent_loop.py` — agent loop
- `financial-engine_v2/cockpit/core/tools.py` — tool definitions
- `financial-engine_v2/cockpit/core/tool_executor.py` — tool execution
- `financial-engine_v2/cockpit/core/config.py` — configuration
- `financial-engine_v2/cockpit/core/strategy.py` — strategy module
- `financial-engine_v2/cockpit/integrations/backend_api.py` — backend API client
- `financial-engine_v2/cockpit/integrations/llamacpp_client.py` — llama.cpp client
- `financial-engine_v2/cockpit/integrations/llamacpp_manager.py` — llama.cpp manager

**Tests to run:**
- `pytest financial-engine_v2/cockpit/tests/` (all cockpit tests — 40+ files)

**Audit checklist:**
- [ ] Verify web.py is primary entrypoint (not TUI main.py)
- [ ] Trace data flow: backend API → cockpit → UI display
- [ ] Check for stale data display (caching without invalidation?)
- [ ] Verify error states shown to user (connection failures, empty results)
- [ ] Check agent mode is default (per project memory)
- [ ] Verify HybridRouter used as LLM client
- [ ] Check tool execution — all tools callable and returning results?
- [ ] Verify preboot health checks
- [ ] Check for missing loading/empty states in UI

**Integration points to verify:**
- Cockpit → Backend API (correct endpoints called?)
- Cockpit → llama.cpp (prompt routing, model selection?)
- Cockpit → Research system (dossier, watchlist scanner?)

---

## Task 8: Docker Service Mesh Audit

**Scope:** Inter-service connectivity, volume mounts, restart policies.

**Files to trace:**
- `financial-engine_v2/docker-compose.yml` — service definitions
- `financial-engine_v2/backend/Dockerfile` — backend image
- `financial-engine_v2/worker/Dockerfile` — worker image
- `financial-engine_v2/.env` (structure only, not values)

**Tests to run:**
- UNTESTED — no dedicated Docker integration tests identified

**Audit checklist:**
- [ ] Verify all services defined: postgres, redis, qdrant, backend, worker, fe_beat
- [ ] Check network_mode: host on all services — implications?
- [ ] Verify volume mounts: pgdata, qdrant storage, backend code, data, scripts
- [ ] Check health checks: postgres has one — do others?
- [ ] Verify depends_on ordering: backend/worker wait for postgres healthy
- [ ] Check restart policies (only fe_beat has `unless-stopped`)
- [ ] Verify env_file references are correct
- [ ] Check for missing restart policies on critical services
- [ ] Verify worker command matches expected queues

**Integration points to verify:**
- Backend → Postgres (connection via host network)
- Backend → Redis (broker connection)
- Backend → Qdrant (vector store connection)
- Worker → same dependencies

---

## Task 9: Postgres and SQLite Schemas Audit

**Scope:** Migrations, constraints, index coverage.

**Files to trace:**
- `financial-engine_v2/backend/app/alembic/versions/0001_init.py` through `0007_add_companies_table.py`
- `financial-engine_v2/backend/app/models/` — all model files
- `financial-engine_v2/backend/app/core/db.py` — DB engine setup
- `financial-engine_v2/cockpit/storage/` — cockpit local storage (likely SQLite)

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_db_integrity.py`
- `pytest financial-engine_v2/backend/tests/test_architecture_invariants.py`

**Audit checklist:**
- [ ] Trace migration chain: 0001 → 0002 → ... → 0007, verify linear
- [ ] Check for missing down migrations (rollback capability)
- [ ] Verify all model fields have appropriate constraints (NOT NULL, UNIQUE, FK)
- [ ] Check index coverage: primary keys, foreign keys, frequently filtered columns
- [ ] Verify SQLAlchemy model definitions match migration state
- [ ] Check cockpit SQLite schema (if exists) — is it well-constrained?
- [ ] Verify no raw SQL queries that bypass ORM (SQL injection risk)
- [ ] Check connection pooling configuration
- [ ] Verify cascade delete/update rules on foreign keys

**Integration points to verify:**
- Alembic migrations → Running DB state (are they in sync?)
- Models → API serialization (any field mismatches?)
- Cockpit SQLite → Backend Postgres (any data duplication?)

---

## Task 10: llama.cpp Inference Layer Audit

**Scope:** GPU utilisation, prompt routing, fallback behaviour.

**Files to trace:**
- `financial-engine_v2/backend/app/services/llamacpp_runtime.py` — LLM runtime
- `financial-engine_v2/backend/app/services/llm.py` — LLM service abstraction
- `financial-engine_v2/backend/app/services/router.py` — model router
- `financial-engine_v2/backend/app/services/router_state.py` — router state
- `financial-engine_v2/backend/app/services/router_metrics.py` — router metrics
- `financial-engine_v2/backend/app/services/router_optimizer.py` — router optimizer
- `financial-engine_v2/backend/app/services/ollama.py` — Ollama service (embeddings only)
- `financial-engine_v2/backend/app/config/model_routing.yaml` — routing config
- `financial-engine_v2/cockpit/integrations/llamacpp_client.py` — cockpit LLM client
- `financial-engine_v2/cockpit/integrations/llamacpp_manager.py` — cockpit LLM manager
- `scripts/gpu_process_guard.sh` — GPU process guard

**Tests to run:**
- `pytest financial-engine_v2/backend/tests/test_model_routing.py`
- `pytest financial-engine_v2/cockpit/tests/test_hybrid_router.py`
- `pytest financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py`
- `pytest financial-engine_v2/cockpit/tests/test_config_router_mode.py`
- `pytest financial-engine_v2/cockpit/tests/test_preboot_router_mode.py`
- `pytest financial-engine_v2/cockpit/tests/test_router_edge_cases.py`

**Audit checklist:**
- [ ] Verify single llama-server on port 8001 in router mode (per project memory)
- [ ] Verify Qwen3-30B-A3B is default model (per project memory)
- [ ] Trace prompt routing: request → router → model selection → inference
- [ ] Check fallback behaviour when llama-server is down
- [ ] Verify GPU process guard script works
- [ ] Check JSON sanitizer in llamacpp_runtime.py
- [ ] Verify Ollama is used ONLY for backend embeddings, not coding/agent workflows
- [ ] Check router metrics collection and optimizer logic
- [ ] Verify model_routing.yaml matches runtime behavior

**Integration points to verify:**
- Extraction pipeline → llama.cpp (which prompts, which model?)
- Cockpit → llama.cpp (agent loop, chat, tool calls)
- Router → model selection (does routing config match actual dispatch?)

---

## Cross-Component Audit Tasks

### Task 11: Data Leakage Detection
- [ ] Verify news data cannot contaminate financial filings RAG collection
- [ ] Check source_registry boundaries between pipeline types
- [ ] Trace Qdrant collection separation (filings vs news vs commentary)
- [ ] Verify prompt construction doesn't mix sources inappropriately

### Task 12: Silent Failure Sweep
- [ ] Grep for bare `except:` and `except Exception` with pass/continue
- [ ] Check for functions returning None/empty on error without logging
- [ ] Verify all Celery tasks have on_failure handlers
- [ ] Check for unchecked HTTP response status codes

### Task 13: Integration Point Matrix
- Build a matrix of all inter-service connections and verify each with evidence:

| From | To | Protocol | Verified? |
|------|----|----------|-----------|
| Backend | Postgres | SQLAlchemy+psycopg2 | |
| Backend | Redis | Celery broker | |
| Backend | Qdrant | qdrant-client | |
| Backend | llama.cpp | HTTP :8001 | |
| Worker | Postgres | Same as backend | |
| Worker | Redis | Celery broker | |
| Worker | Qdrant | qdrant-client | |
| Cockpit | Backend | HTTP :8000 | |
| Cockpit | llama.cpp | HTTP :8001 | |
| Beat | Redis | Celery beat | |

---

## Execution Strategy

**Phase 1 — Parallel code trace (Tasks 1–10):** Launch sub-agents to read and trace execution paths for each component. No tests yet — pure code reading.

**Phase 2 — Test execution:** Run all identified test suites. Record pass/fail/skip counts. Note UNTESTED areas.

**Phase 3 — Cross-component audit (Tasks 11–13):** Data leakage, silent failures, integration verification. These depend on Phase 1 findings.

**Phase 4 — Scoring and report:** Score each component 1–10 on the 5 axes. Rank inefficiencies. Rank improvements by impact/effort.

**Estimated sub-agent allocation:**
- 5 parallel agents for Phase 1 (2 components each)
- 1 agent for Phase 2 (sequential test runs)
- 2 parallel agents for Phase 3 (leakage + silent failures)
- 1 agent for Phase 4 (synthesis)

**Budget note:** At ~$1/agent, 9 agents ≈ $9. Within $10 budget.
