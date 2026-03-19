# Cockpit chat latency analysis

Analysis of why cockpit chats can feel slow even when the LLM model is already pulled. Focus: end-to-end path from user message to assistant reply (TUI and web UI).

## Summary

Slowness is likely from **pre-LLM context gathering** (DB + RAG + optional PDF excerpts), **large prompts**, and **Ollama inference time**. Streaming is used for the main LLM call in the web UI, but context is built fully before any token is streamed, and retries are non-streaming.

---

## 1. Context gathering (pre-LLM) — highest impact

Before the LLM is called, `build_chat_response` runs `_gather_local_context_with_timeout`, which can take up to **60 seconds** (default `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS`). All of this is **blocking** and **sequential**.

### What runs in `gather_local_context` (tools.py)

| Step | Operational mode | Deep mode | Notes |
|------|------------------|------------|--------|
| `file_indexer.list_recent_reports` | 1 call | 1 call | File system / index |
| `file_indexer.search_text(pattern=query)` | 1 call | 1 call | Text search |
| `_load_ticker_context` | 1 call | 1 call | **5 DB queries**: get_docs, get_announcement_context, get_financials, get_extraction_failures, get_low_confidence_financials. Cached 15s per ticker. |
| PDF excerpts | up to 5 docs | up to 20 docs | If `context_rows` is empty, **PyMuPDF** extracts excerpts (up to 1500/3500 chars each). Per-doc I/O + parsing. |
| `_load_price_context` | 1 call | 1 call | Backend API or price source |
| Price horizons (deep only) | — | **4 calls** | 1y, 3y, 5y, 10y via `get_price_context_for_window` |
| Qual context (RAG) | 2 readers | 2 readers | **Company** + **News** readers; each calls **backend `query_rag`** → Ollama embed + Qdrant search |

So for a typical “analyse BHP” in operational mode you get:

- Several DB round-trips
- Optional PDF excerpt extraction (can be slow for many/large PDFs)
- One price context call
- **Two backend RAG calls** (each: embed query via backend → Ollama embed, then Qdrant search)

If the backend and the cockpit share the same Ollama instance, embedding requests and the main chat request can contend.

---

## 2. LLM call and retries

- **Main call**: Uses streaming when the UI passes `on_chunk` (web UI does; TUI uses same `CockpitApp`, so streaming is used). So first token can still be delayed by context building.
- **Timeout**: `llm_timeout_seconds` default **300** (config `llm.timeout_seconds`).
- **Retries**: Up to **3 extra full LLM calls** with **stream=False** when:
  - Response looks like prompt echo → retry
  - Off-topic analysis → retry
  - Deep mode: framework-only or contract violation → retries

So a single turn can trigger 1 streamed call + up to 3 non-streamed retries, all with the same large prompt.

---

## 3. Prompt size

- System prompt is large (main analysis template, evidence mandate, sections).
- **Local evidence JSON**: operational budget defaults to 16k chars (`balanced`) or 32k chars (`max-depth`); deep mode remains effectively unbounded (sanitized only).
- **Web evidence JSON** (if enabled): operational budget defaults to 9k chars (`balanced`) or 18k chars (`max-depth`).
- Larger prompts → more tokens to process → longer time to first token and to completion.

`/context-profile max-depth` can therefore increase analysis coverage, but it also increases prompt assembly and generation cost.

---

## 4. “Model already pulled” vs perceived slowness

- “Model pulled” only means the model is on disk and loadable. It does **not** mean:
  - Context gathering is fast (it’s independent of Ollama).
  - The first inference is warm (first request after startup can be slower).
  - Backend RAG isn’t also calling Ollama (embedding model), which can queue with chat.
- So chats can still feel slow even when the chat model is already pulled.

---

## 5. Recommendations (prioritised)

### Quick wins

1. **Show timings in the TUI**  
   The app already records `timings` (e.g. `context_ms`, `llm_ms`, `web_ms`) and the web UI has `_record_chat_latency`. Expose a compact timing line in the TUI (e.g. “context 2.1s | llm 4.3s”) so you can see whether the bottleneck is context or LLM.

2. **Tighten context timeout for interactive use**  
   Set `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS=20` (or 30) so slow context fails fast instead of feeling like a hang. Optional: surface a “context timed out” message in the UI.

3. **Reduce operational-mode context volume**  
   In `tools.py` `gather_local_context`, consider lowering operational defaults slightly (e.g. `docs_limit`, `snippets_limit`, `rag_company_limit`, `rag_news_limit`) to reduce DB work, PDF work, and RAG calls. Keep deep mode as-is for quality.

4. **Optional: disable or shortcut qual context for speed**  
   If qual context (RAG) is enabled, it adds two backend calls per turn. For a quick test, disable it in config or add a “fast” mode that skips RAG for simple queries.

### Medium-term

5. **Parallelise context where possible**  
   E.g. run DB ticker context, file_indexer, and (where safe) price + RAG in parallel (thread pool or async), then merge. This would require refactoring `gather_local_context` and possibly the backend API client.

6. **Stream context-building progress**  
   Show “Loading context…”, “Searching docs…”, “Calling RAG…” so the user sees activity instead of a long blank wait.

7. **Retries with streaming**  
   Use `on_chunk` in retry paths (or a single consolidated retry with streaming) so the user sees output during retries instead of waiting for a full non-streamed reply.

### Observability

8. **Structured timing logs**  
   In `chat.py` around the LLM call and in `tools.py` at the start/end of `gather_local_context`, log:
   - `context_gather_ms`, `context_breakdown` (e.g. db_ms, rag_ms, pdf_ms if you add per-step timing),
   - `llm_first_token_ms` (if you can hook into the stream),
   - `llm_total_ms`.

9. **Backend RAG timeouts**  
   Ensure the backend `query_rag` (and any client-side timeout calling it) is bounded (e.g. 10–15s) so a slow embed or Qdrant doesn’t hold the whole turn.

---

## 6. Where to add timing (code pointers)

- **Context total**: `chat.py` already has `context_started_at` / `context_ms` around `_gather_local_context_with_timeout`. Ensure this is logged (e.g. at info level with `mode`, `ticker`, `context_ms`).
- **Per-step context**: In `tools.py` `gather_local_context`, add `time.perf_counter()` around: DB block, PDF excerpts block, price load, qual_context company/news calls. Log or attach to a debug payload.
- **LLM**: `chat.py` already has `llm_started_at` and `llm_ms`. Log `prompt_len`, `context_ms`, `llm_ms` together so you can correlate prompt size and context time with LLM time.

---

## Files touched by this analysis

- `financial-engine_v2/cockpit/core/chat.py` — `build_chat_response`, `_gather_local_context_with_timeout`, LLM call and retries.
- `financial-engine_v2/cockpit/core/tools.py` — `gather_local_context`, `_load_ticker_context`, `_extract_pdf_excerpt`, `_query_qual_context_reader`.
- `financial-engine_v2/cockpit/integrations/ollama_client.py` — `chat(..., stream=..., on_chunk=...)`.
- `financial-engine_v2/cockpit/integrations/qual_context.py` — `QualContextReader.query` → backend `query_rag`.
- `financial-engine_v2/backend/app/services/rag.py` — `query_rag` (embed + Qdrant).
- `financial-engine_v2/cockpit/ui/app.py` — streaming, `_on_chunk`, `_record_chat_latency`.
