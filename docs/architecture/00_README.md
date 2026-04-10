# Architecture documentation

Overview of the architecture docs in this folder and what each covers.

> **SYSTEM_CONTRACT.md is the authoritative system specification.** All architecture docs describe *how* the system works; the contract defines *what must not be violated*. When any doc conflicts with the contract, the contract wins. Read [SYSTEM_CONTRACT.md](SYSTEM_CONTRACT.md) before making changes to any subsystem described below.

| Document | Purpose |
|----------|---------|
| **[SYSTEM_CONTRACT.md](SYSTEM_CONTRACT.md)** | **Non-negotiable system invariants — data integrity, pipeline rules, agent behavior** |
| [00_README.md](00_README.md) | Index and purpose of each architecture doc |
| [01_system_overview.md](01_system_overview.md) | High-level system overview and components |
| [02_runtime_topology.md](02_runtime_topology.md) | Runtime topology and deployment layout |
| [03_data_model.md](03_data_model.md) | Data model and persistence |
| [04_ingestion_pipeline.md](04_ingestion_pipeline.md) | Ingestion pipeline design and flow |
| [05_pdf_extraction_and_chunking.md](05_pdf_extraction_and_chunking.md) | PDF extraction and chunking strategy |
| [06_embeddings_and_vector_store.md](06_embeddings_and_vector_store.md) | Embeddings and vector store (Qdrant) |
| [07_rag_contract.md](07_rag_contract.md) | RAG API contract and behavior |
| [08_backfill_contract.md](08_backfill_contract.md) | Backfill API contract and behavior |
| [09_worker_and_celery_contract.md](09_worker_and_celery_contract.md) | Worker and Celery task contract |
| [model-routing.md](model-routing.md) | Multi-model routing, role assignment, and queue selection |
| [10_failure_model.md](10_failure_model.md) | Failure model and error handling |
| [11_engineering_discipline.md](11_engineering_discipline.md) | Pre-merge checklist and engineering discipline guardrails |
| [11_rebuild_and_recovery.md](11_rebuild_and_recovery.md) | Rebuild and recovery procedures |
| [12_evaluation_and_drift_monitoring.md](12_evaluation_and_drift_monitoring.md) | Evaluation and drift monitoring, including the real-document gold eval pilot, local MLflow tracking, and read-only DuckDB analysis |
| [13_security_and_secrets.md](13_security_and_secrets.md) | Security and secrets management |
| [14_roadmap_and_modules.md](14_roadmap_and_modules.md) | Roadmap, module boundaries, and future capability: Autonomous Dev Optimization Loop (deferred) |
| [15_news_substrate.md](15_news_substrate.md) | Canonical news substrate: one RAG DB, layers, orchestrator, verification |
| [16_currency_and_fx_policy.md](16_currency_and_fx_policy.md) | Currency and FX handling: current ok_low_confidence gate, what changes downstream, roadmap for FX conversion |
| [17_analysis_modules.md](17_analysis_modules.md) | Phase 3 analysis modules: 6-module architecture (balance_sheet, ROIC, valuation, risk, catalysts, moat), Protocol contract, D1/D2 layers, orchestration, data flow, quality assurance |
| [17_agentic_chat_architecture.md](17_agentic_chat_architecture.md) | Agentic chat transformation design history: tool-calling agent loop, structured output, migration rationale (historical document) |
| [18_cockpit_memory.md](18_cockpit_memory.md) | Cockpit memory system: 5 storage layers, context assembly flow, session lifecycle, ticker intelligence model, retention policy |
| [19_backend_api_surface.md](19_backend_api_surface.md) | Live backend route inventory, auth boundaries, compatibility aliases, and route grouping |
| [20_chat_learning_loop.md](20_chat_learning_loop.md) | Chat learning loop: composite quality metric, fast path (preference learning), slow path (skill patching), Rule 0 integration, rollback protection |

Numbering is historical: both `11_engineering_discipline.md` and `11_rebuild_and_recovery.md` are active.
