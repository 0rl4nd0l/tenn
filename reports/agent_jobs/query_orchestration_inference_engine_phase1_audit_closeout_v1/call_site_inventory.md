# Call-Site Inventory

## `generate_json`

Current routed facade:

- `financial-engine_v2/backend/app/services/llm.py:403-491` defines `generate_json()`.
- `financial-engine_v2/backend/app/worker_tasks.py:92-100` exposes Celery task `llm_generate_json`.
- `financial-engine_v2/backend/app/services/multipass_extraction.py:3595-3604` calls `generate_json()` with `component=multipass_extraction` and optional `requested_model`.
- `financial-engine_v2/backend/app/services/tenn_chat.py:690-700` calls `generate_json()` with `component=tenn_chat`, `operation=chat_with_tenn`, and `requested_base_url=settings.llamacpp_url`.
- `financial-engine_v2/backend/app/services/news_memo_extractor.py:179-221` defaults `llm_fn` to `generate_json()` and passes memo metadata when supported.
- `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:107-147` defaults `llm_fn` to `generate_json()` and passes memo metadata when supported.
- `financial-engine_v2/backend/app/services/thesis_watchdog.py:35-86` defaults `llm_fn` to `generate_json()`.
- `financial-engine_v2/backend/app/services/thesis_audit.py:491-522` imports `generate_json()` lazily when no injected `llm_fn` is supplied.

Direct or adjacent generation paths that bypass the facade:

- `financial-engine_v2/backend/app/modules/catalysts.py:178-188` calls `generate_json_llamacpp()` directly.
- `financial-engine_v2/backend/app/modules/moat.py:185-197` calls `generate_json_llamacpp()` directly.
- `financial-engine_v2/backend/app/modules/risk.py:200-216` calls `generate_json_llamacpp()` directly.
- `financial-engine_v2/backend/app/services/research_synthesis.py:123-142` builds a direct llama.cpp chat-completions request.
- `financial-engine_v2/backend/app/services/cockpit_service.py` uses Cockpit `LlamaCppClient`, not the backend `llm.py` facade.
- `financial-engine_v2/cockpit/**` contains Cockpit agent/runtime clients and is a separate contract surface.
- Script and test harness paths also exercise the facade or local lookalikes: `scripts/benchmark_pdf_extraction.py:419`, `financial-engine_v2/scripts/test_commentary_pipeline.py:556`, `scripts/test_run_isolated_docling_control.py:210`, and script-local embedding helpers in `scripts/build_qualitative_context_db.py` / `financial-engine_v2/scripts/embed_docs_to_qdrant.py`.

## `embed_texts`

Current routed facade:

- `financial-engine_v2/backend/app/services/llm.py:374-400` defines `embed_texts()`.
- `financial-engine_v2/backend/app/worker_tasks.py:103-111` exposes Celery task `llm_embed_texts`.
- `financial-engine_v2/backend/app/main.py:1454-1461` embeds a startup dimension probe.
- `financial-engine_v2/backend/app/services/pipeline.py:299-329` embeds document chunks in batches.
- `financial-engine_v2/backend/app/services/rag.py:405-410` embeds news queries.
- `financial-engine_v2/backend/app/services/rag.py:479-494` embeds document RAG queries and separately records a routing decision.
- `financial-engine_v2/backend/app/services/analysis_rag_adapter.py:42-48` embeds analysis-module RAG queries.
- `financial-engine_v2/backend/app/services/hybrid_retriever.py:71-79` embeds hybrid retrieval queries.
- `financial-engine_v2/backend/app/services/reranker.py:15-22` embeds reranker text.
- `financial-engine_v2/backend/app/services/framework_classifier.py:25-33` embeds framework classification text.
- `financial-engine_v2/backend/app/services/chat_quality_scorer.py:51-54` embeds chat session coherence text.

Adjacent embedding paths:

- `financial-engine_v2/backend/app/services/embeddings.py:222-280` owns low-level embedding backend resolution and Ollama/llama.cpp dispatch.
- `financial-engine_v2/scripts/embed_docs_to_qdrant.py` defines a script-local `embed_texts()`.
- `scripts/build_qualitative_context_db.py` defines a script-local `embed_texts()`.
- `scripts/build_news_context_db.py` and `scripts/news_pipeline/chunk_builder.py` call injected context embedding functions.
- `scripts/pdf_rag.py:416` and `scripts/test_pdf_rag_company_validation.py:108` use local/injected embedding helpers outside the backend facade contract.

## `route_request`

- `financial-engine_v2/backend/app/services/router.py:751-820` defines `route_request()`.
- `financial-engine_v2/backend/app/services/llm.py:108-109` exposes `get_routing_decision()` as a thin wrapper.
- `financial-engine_v2/backend/app/services/llm.py:381-388` routes embedding requests.
- `financial-engine_v2/backend/app/services/llm.py:410` routes JSON generation requests.
- `financial-engine_v2/backend/app/celery_app.py:36-42` routes Celery `llm_generate_json` task dispatch.

## `llm_fn`

- `financial-engine_v2/backend/app/services/news_memo_extractor.py:179-221` accepts injected `llm_fn`, detects whether it supports `metadata`, and falls back to legacy `base_url/model/prompt` call shape.
- `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:107-147` follows the same injection/legacy-callable pattern.
- `financial-engine_v2/backend/app/services/thesis_watchdog.py:35-86` accepts injected `llm_fn` and calls it with `prompt`, `metadata`, and `timeout`.
- `financial-engine_v2/backend/app/services/thesis_audit.py:491-522` accepts injected `llm_fn`, calls the current keyword shape, and falls back to a positional prompt after `TypeError`.

## Migration Risk Classification

- LOW: adding typed request/result containers and adapters in `llm.py` while keeping existing function signatures.
- MEDIUM: migrating memo extractors because `llm_fn` injection supports legacy callables.
- MEDIUM: moving Celery dispatch to persist a route decision, because worker execution currently re-routes.
- HIGH: unifying Cockpit agent runtime clients with backend inference, because Cockpit has separate provider and interaction contracts.
- HIGH: changing module D2 direct calls without preserving optional/no-LLM behavior.
