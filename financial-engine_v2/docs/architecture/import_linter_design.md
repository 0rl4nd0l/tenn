# import-linter Layer Configuration Design

This document maps the SYSTEM_CONTRACT.md layers to the actual Python package
structure. It is the input for a follow-up session that writes the `.importlinter`
config file.

---

## 1. SYSTEM_CONTRACT Layers (§2.1, verbatim)

| Layer      | Responsibility                   |
|------------|----------------------------------|
| Ingestion  | Acquire raw data                 |
| Extraction | Structure raw data               |
| Storage    | Persist structured + vector data |
| Retrieval  | Query and rank relevant data     |
| Analysis   | Interpret and derive insights    |
| Client     | Present and orchestrate          |

---

## 2. Current `services/` Sub-Module List

```
analysis_report_schema.py
announcement_importance.py
asx.py
channel_registry.py
cockpit_service.py
commentary_decay.py
commentary_ingest.py
commentary_memo_extractor.py
docling_extract.py
embeddings.py
framework_classifier.py
framework_retriever.py
hybrid_retriever.py
llamacpp_embeddings.py
llamacpp_runtime.py
llm.py
marketindex_headed_recovery.py
multipass_extraction.py
news_memo_extractor.py
ollama.py
openbb_staging.py
pipeline.py
pipeline_service.py
rag.py
reranker.py
research_context_builder.py
research_synthesis.py
retrieval_orchestrator.py
router.py
router_metrics.py
router_optimizer.py
router_state.py
session_memory.py
source_registry.py
source_weighting.py
speaker_turn_detector.py
storage.py
strategy_controller.py
structured_chunking.py
system_analyzer.py
tenn_chat.py
transcript_watcher.py
youtube_transcript_fetcher.py
validation/                     (new — pandera schemas)
analysis/                       (subdir — analysis modules)
```

---

## 3. Proposed Mapping: Sub-Module → Layer

### Ingestion
| Module | Rationale |
|--------|-----------|
| `pipeline.py` | Core ingestion orchestrator (download → extract → embed → persist) |
| `pipeline_service.py` | Pipeline service wrapper |
| `asx.py` | ASX data provider |
| `marketindex_headed_recovery.py` | MarketIndex headed browser recovery |
| `openbb_staging.py` | Market data staging from OpenBB |
| `commentary_ingest.py` | Commentary chunk ingestion |
| `transcript_watcher.py` | Transcript file watcher |
| `youtube_transcript_fetcher.py` | YouTube transcript download |
| `news_memo_extractor.py` | News memo extraction |
| `providers/` (package) | All external data source providers |

### Extraction
| Module | Rationale |
|--------|-----------|
| `docling_extract.py` | PDF → StructuredDocument (tables + sections) |
| `multipass_extraction.py` | 4-pass LLM extraction pipeline |
| `commentary_memo_extractor.py` | Commentary memo LLM extraction |
| `structured_chunking.py` | Section-aware chunking |
| `speaker_turn_detector.py` | Speaker turn detection in transcripts |
| `announcement_importance.py` | Announcement importance scoring |
| `framework_classifier.py` | Document framework classification |
| `validation/` (package) | Pandera extraction output schemas |

### Storage
| Module | Rationale |
|--------|-----------|
| `storage.py` | Postgres storage operations |
| `embeddings.py` | Qdrant upsert, collection management |
| `llamacpp_embeddings.py` | LLM embedding generation |
| `ollama.py` | Ollama embedding client |
| `models/` (package) | SQLAlchemy ORM models |
| `alembic/` (package) | Database migrations |

### Retrieval
| Module | Rationale |
|--------|-----------|
| `hybrid_retriever.py` | Dense + sparse search |
| `retrieval_orchestrator.py` | Query routing and context bundling |
| `rag.py` | RAG query composition |
| `reranker.py` | Result reranking |
| `framework_retriever.py` | Framework-based retrieval |
| `source_registry.py` | Source registration and lookup |
| `source_weighting.py` | Source weight configuration |
| `commentary_decay.py` | Temporal decay for commentary |
| `research_context_builder.py` | Research context assembly |

### Analysis
| Module | Rationale |
|--------|-----------|
| `analysis/` (subdir) | All analysis modules (financial_metrics, risk_module, etc.) |
| `analysis_report_schema.py` | Analysis report output schema |
| `research_synthesis.py` | Research synthesis and summarization |
| `strategy_controller.py` | Strategy system controller |
| `system_analyzer.py` | System analysis utilities |

### Client
| Module | Rationale |
|--------|-----------|
| `tenn_chat.py` | Chat orchestration |
| `cockpit_service.py` | Cockpit service layer |
| `session_memory.py` | Chat session memory |
| `channel_registry.py` | Channel registration |
| `routes/` (package) | API route handlers |
| `api/` (package) | REST endpoints |

### Cross-Cutting (not assignable to a single layer)
| Module | Rationale |
|--------|-----------|
| `llm.py` | LLM call abstraction (used by Extraction, Retrieval, Analysis) |
| `llamacpp_runtime.py` | llama.cpp HTTP client (used by Extraction, Chat) |
| `router.py` | Task-type classifier + model selector |
| `router_metrics.py` | Router metrics collection |
| `router_optimizer.py` | Adaptive model optimization |
| `router_state.py` | Router state management |
| `core/` (package) | Config, settings |
| `tasks/` (package) | Celery worker dispatch |

---

## 4. Ambiguous Sub-Modules

| Module | Ambiguity | Resolution Needed |
|--------|-----------|-------------------|
| `llm.py` | Used by Extraction (generate_json), Retrieval (embed_texts), Analysis (synthesis). Functionally cross-cutting. | Treat as `core` infrastructure, exempt from layer constraints. |
| `llamacpp_runtime.py` | HTTP client for llama.cpp — used by extraction AND chat. | Same as `llm.py` — core infrastructure. |
| `commentary_memo_extractor.py` | Extracts memos from commentary (Extraction), but is called during ingestion pipeline. | Assign to Extraction; ingestion calls it as a service. |
| `news_memo_extractor.py` | Similar to commentary_memo_extractor — extraction logic invoked during ingestion. | Assign to Extraction (consistent with above). |
| `pipeline.py` | Orchestrates ingestion, extraction, storage, and embedding. Crosses 3 layers. | Assign to Ingestion as the entry coordinator. Allow it to import from Extraction and Storage. |
| `rag.py` | Thin wrapper that composes retrieval and LLM calls. | Assign to Retrieval. |
| `router*.py` | Model routing is infrastructure, not business logic. | Treat as `core`. |

---

## 5. Proposed Target Package Structure

To enable clean import-linter enforcement, `services/` should be reorganized
into layer-aligned sub-packages. This is a **future refactor target**, not an
immediate action.

```
services/
├── ingestion/
│   ├── pipeline.py
│   ├── pipeline_service.py
│   ├── asx.py
│   ├── marketindex_headed_recovery.py
│   ├── openbb_staging.py
│   ├── commentary_ingest.py
│   ├── transcript_watcher.py
│   └── youtube_transcript_fetcher.py
├── extraction/
│   ├── docling_extract.py
│   ├── multipass_extraction.py
│   ├── commentary_memo_extractor.py
│   ├── news_memo_extractor.py
│   ├── structured_chunking.py
│   ├── speaker_turn_detector.py
│   ├── announcement_importance.py
│   ├── framework_classifier.py
│   └── validation/
│       └── extraction_schemas.py
├── storage/
│   ├── storage.py
│   ├── embeddings.py
│   ├── llamacpp_embeddings.py
│   └── ollama.py
├── retrieval/
│   ├── hybrid_retriever.py
│   ├── retrieval_orchestrator.py
│   ├── rag.py
│   ├── reranker.py
│   ├── framework_retriever.py
│   ├── source_registry.py
│   ├── source_weighting.py
│   ├── commentary_decay.py
│   └── research_context_builder.py
├── analysis/
│   ├── (existing analysis/ subdir contents)
│   ├── analysis_report_schema.py
│   ├── research_synthesis.py
│   ├── strategy_controller.py
│   └── system_analyzer.py
├── client/
│   ├── tenn_chat.py
│   ├── cockpit_service.py
│   ├── session_memory.py
│   └── channel_registry.py
└── core/
    ├── llm.py
    ├── llamacpp_runtime.py
    ├── router.py
    ├── router_metrics.py
    ├── router_optimizer.py
    └── router_state.py
```

**Layer dependency rules (enforced by import-linter):**

```
Client → Analysis → Retrieval → Storage
                  → Extraction → Storage
Ingestion → Extraction → Storage

Core ← (all layers may import from core)
```

**Forbidden imports:**
- Client must NOT import from models/ directly (use services)
- Client must NOT import from providers/ (use ingestion services)
- Storage must NOT import from Retrieval or Analysis
- Extraction must NOT import from Retrieval or Client

---

## Next Steps

1. Review this mapping with the user
2. Decide: write `.importlinter` config against current flat structure (coarser
   granularity) or refactor services/ first (cleaner enforcement)
3. If flat config: use module-level allowlists for cross-cutting concerns
4. If refactor first: separate session to move files + update imports
