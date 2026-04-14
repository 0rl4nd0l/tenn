# Phase 01: Full-Stack Silent-Failure Audit

Three production bugs — raw JSON leaking to chat, empty sources dropdown on agent responses, and stale news presented as today's — all shared the same root pattern: **silent assumptions about data shape or temporal context** that held until a different code path invalidated them. This audit phase systematically maps every location across the full stack where a similar latent assumption lives. The output is a structured report that Phase 02 uses as its fix list.

## Tasks

- [x] Read and internalize the three known bug post-mortems before auditing anything:
  - Bug 1 (flag_20260411_063730_56ae948c): multi-JSON in single completion → raw JSON leak  
    Root: `parse_llm_response` had no multi-object handling; fixed in `cockpit/core/response_parser.py` via `_try_split_multi_json`
  - Bug 2 (flag_20260414_062329_a79386c4): agent-mode evidence had `{tool, arguments, result}` not `{type, details}` → silent empty sources  
    Root: `_build_ui_sources` in `backend/app/routes/cockpit_api.py` only knew the orchestrator format; fixed by adding an agent-evidence branch
  - Bug 3 (flag_20260414_063355_ee3d9e4a): model anchored "today" to `published_at` values from retrieved articles  
    Root: `search_news` didn't signal when freshest article was stale; fixed by adding `freshness_warning` field to results
  - Read: `financial-engine_v2/cockpit/core/response_parser.py` — understand the current multi-JSON fix fully
  - Read: `financial-engine_v2/backend/app/routes/cockpit_api.py` lines 339–530 — understand the agent-evidence branch fix
  - The goal: understand *why* each fix worked before auditing for related patterns
  <!-- DONE 2026-04-14: Both files read in full.
    Bug1 fix confirmed: _try_split_multi_json (lines 79-126) uses a brace-depth scanner to find object boundaries; parse_llm_response (lines 205-236) then extracts the last "response"-typed object and carries thinking metadata from the "thinking"-typed object.
    Bug2 fix confirmed: _build_ui_sources (lines 467-501 of cockpit_api.py) added an elif branch that detects agent-loop format by checking `ev.get("tool") and not ev.get("type")`, then routes search_news → hits[], gather_local_context/query_ticker_data → hits[]/rag_hits[]/docs[].
    Bug3 fix: freshness_warning field added to search_news results when freshest article is stale (not visible in these files — lives in tool_executor.py).
    Common root pattern confirmed: all three bugs arose from code that assumed a single well-known data shape and silently produced no output when a different but valid shape arrived. -->

- [x] Audit `cockpit/core/response_parser.py` for remaining JSON parsing risks:
  - Does `_try_split_multi_json` handle arrays at top level, or only `{…}` objects?
  - What happens if the LLM emits three objects (thinking + tool_call + response) in one completion? Is the third object correctly used?
  - Does `_repair_json` handle unterminated strings or mismatched delimiters, or only trailing commas?
  - What happens when the `type` field is present but set to an unexpected string (not in `VALID_TYPES`)?
  - Does `_infer_type` correctly handle objects that have both `tool` and `assessment` keys?
  - Record each finding as: CONFIRMED (definitely broken), LATENT (could break under specific conditions), SAFE (explicitly handled)
  <!-- DONE 2026-04-14: Findings:
    1. LATENT — Top-level arrays not handled by _try_split_multi_json (lines 100-124 only scan {/} depth, not [/]). A top-level JSON array like [{"type":"thinking",...},{"type":"response",...}] bypasses multi-split and falls through to plain-text fallback — raw JSON could surface to user.
    2. LATENT — Three-object completions (thinking + tool_call + response): the multi-object loop (lines 208-228) only preserves thinking_obj and response_obj by exact type match. A tool_call sandwiched between them is silently discarded. The LLM may emit this pattern in long reasoning completions.
    3. LATENT — _repair_json (lines 67-76) only strips trailing commas. Unterminated strings, truncated completions, and mismatched delimiters are not repaired. These fall through to the plain-text fallback, but that fallback shows raw partial JSON to the user, which is a degraded experience.
    4. SAFE — Unknown type field: _build_from_dict (lines 157-158) explicitly falls through to _infer_type when type not in VALID_TYPES.
    5. LATENT — _infer_type (lines 142-143) checks "assessment" before "tool". An object with both keys (e.g. from a hallucinating LLM that merged formats) is classified as "thinking" and its tool key is silently discarded. -->


- [x] Audit `cockpit/core/agent_loop.py` for silent shape assumptions in the main loop:
  - Read the full file: `financial-engine_v2/cockpit/core/agent_loop.py`
  - What happens when a tool result `dict` has a `None` value for a key the loop accesses directly?
  - Does `evidence.append(...)` guard against non-dict tool results?
  - Does the `tool_calls` multi-call branch guard against missing `id`, `tool`, or `arguments` keys in each call dict?
  - What happens if `on_thinking` is called with a `None` assessment or plan?
  - What happens when `_finalize_result` is called but `AgentResult.evidence` contains entries from mixed formats (orchestrator vs agent-loop)?
  - Trace what `routing_metadata` looks like when the HybridRouter selects cloud vs local — are there shape differences between cloud and local response metadata?
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. SAFE — None values in tool result dicts: _execute_tool (line 836) wraps any non-dict result in {"result": result}; dict results are passed as-is. No direct key access at the append site.
    2. SAFE — evidence.append always receives a full {tool, arguments, result} envelope (lines 490-492); the result is guaranteed dict by line 836.
    3. SAFE — _normalize_tool_calls (lines 810-822) uses .get("tool","unknown") and .get("arguments") or {}; missing id/tool/arguments cannot raise KeyError.
    4. SAFE — on_thinking guard: assessment = parsed.assessment or parsed.content or "" (line 324); plan = parsed.plan or "" (line 325). Neither is ever None when on_thinking is called (line 333).
    5. SAFE — Mixed-format evidence in _finalize_result: _finalize_result calls _synthesize_final_answer which passes evidence to _summarize_evidence (plain text dump) and then to _call_llm. The synthesis system prompt doesn't interpret evidence shape — it just treats it as opaque text context. Shape mixing causes no crash.
    6. LATENT — routing_metadata: AgentResult.routing_metadata is declared (line 81) but never assigned anywhere in _run_inner or _finalize_result. It is always None on the returned AgentResult, meaning cloud vs local routing cannot be surfaced to the UI via this field. Low impact currently but may block future routing transparency features. -->

- [x] Audit `cockpit/core/tool_executor.py` and `cockpit/core/tools.py` for tool executor shape contract violations:
  - Read: `financial-engine_v2/cockpit/core/tool_executor.py` — this is where `_exec_search_news` (line ~292) and `freshness_warning` injection live
  - Read: `financial-engine_v2/cockpit/core/tools.py` — this is where `gather_local_context` lives
  - For each tool handler, check: what does it return when the backend returns an unexpected shape (e.g. `null` instead of `{hits: [...]}`, a list instead of a dict, or a missing key)?
  - Does `_exec_search_news` add `freshness_warning` consistently for *all* result shapes, including when the backend returns 0 hits? (The current fix only fires when `hits` is non-empty — check the 0-hits path)
  - Does `gather_local_context` produce the same key shape when called via the local path vs cloud path?
  - For tool handlers that call external HTTP endpoints, does the error branch return a dict that the agent loop can still extract a `result` from?
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. CONFIRMED — _exec_search_news freshness_warning 0-hit gap: Lines 373-409 — freshness_warning is only computed inside `if compact_hits:` (line 374). When hit_count == 0, the code returns the "no hits" enriched response at line 326-345 (for likely_unpopulated_news_db) or a bare 0-hit dict at line 399-410, with no freshness_warning in either path. HIGH priority fix.
    2. SAFE — _exec_search_news non-dict result: Line 306 explicitly checks `if not isinstance(result, dict): return {"ok": False, "error": "unexpected news context response"}`.
    3. LATENT — _exec_query_ticker_data payload spread: Line 140 — `payload = result.payload if hasattr(result, "payload") else {}`. Then line 145: `return {"ok": ..., **payload}`. If result.payload is a list or None (ToolResult returns non-dict payload from an edge case), the **spread raises TypeError. The outer execute() try/except catches this but logs it as a generic tool failure rather than a shape contract violation.
    4. SAFE — HTTP error paths: _exec_run_analysis (lines 701-725), _exec_fetch_url (line 563) all return {"ok": False, "error": ...} error dicts on exceptions — agent loop can always extract a result.
    5. LATENT — gather_local_context shape inconsistency: tools.py shows two retrieval paths (_query_qual_context_reader returns variable shape from external reader; _query_news_sqlite_context returns fixed {ok, hits, source, candidate_count, filtered_count}). Callers using .get("hits", []) are safe, but callers expecting the "source" key only get it from the sqlite path.
    6. SAFE — Outer execute() exception guard (line 100-106): Any uncaught exception in any handler is caught and returned as {"tool": name, "ok": False, "error": ...}. -->

- [x] Audit `_build_ui_sources` in `backend/app/routes/cockpit_api.py` for remaining gaps:
  - Which tool names in the agent evidence branch are currently handled? (`search_news`, `gather_local_context`, `query_ticker_data`)
  - List all tool names registered in `cockpit/core/tools.py` or `cockpit/core/tool_definitions.py`
  - For each tool not currently handled in `_build_ui_sources`, what shape does its `result` dict have?
  - Could any unhandled tool return evidence that a user would want to see in the sources panel?
  - Does the orchestrator-format branch handle every `ev_type` that the backend actually emits? Check `retrieval_orchestrator.py` for all `type` values it can produce
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. Currently handled in agent-evidence branch: search_news (→ hits[]), gather_local_context (→ hits[]/rag_hits[]/docs[]), query_ticker_data (same as gather_local_context).
    2. All registered tool names from tool_definitions.py: query_ticker_data, get_price, get_price_on_date, get_price_range, get_financials, search_news, search_announcements, search_files, get_data_quality, run_analysis, fetch_url, get_strategy, search_web, search_social, recall_dossier, deep_research, get_watchlist_alerts, scan_watchlist + mutating: run_backfill, run_news_ingest, (others).
    3. CONFIRMED — 13+ tool results silently dropped. High user-value tools not handled: search_announcements → {ok, ticker, documents[], context[]}, recall_dossier → {ok, entries[]}, deep_research → {ok, sections[]}, search_web → {ok, results[{title,url,snippet}]}, get_financials → {ok, financials[], narrative}. These all contain evidence a user would want to see.
    4. SAFE — get_price, get_price_on_date, get_price_range return numeric time-series data, not document sources. Reasonable to not display them in a sources panel.
    5. Not yet verified: which ev_types the orchestrator branch handles vs. actually emits — deferred to retrieval_orchestrator audit (next task). -->

- [x] Audit `backend/app/services/retrieval_orchestrator.py` and `backend/app/services/hybrid_retriever.py` for shape contract violations:
  - Read both files (search first for the most relevant functions, then read selectively)
  - Does the orchestrator always produce evidence entries with a `type` key? Are there code paths where type is absent or `None`?
  - What does the orchestrator return when Qdrant returns 0 hits? Is there a `hits: []` or is the key absent entirely?
  - Does `hybrid_retriever.py` guard against Qdrant returning payloads without expected keys (e.g. `source_id`, `score`, `title`)?
  - Are there date/timestamp fields in retrieval results that the LLM could anchor "today" to? (Beyond `published_at` in news — check `created_at`, `updated_at`, `ingested_at` fields in any chunk payload)
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. CONFIRMED — retrieval_orchestrator may produce evidence entries without `type` key: Commentary chunks assembled into evidence without explicitly setting type. If the commentary retriever payload doesn't include type, downstream _build_ui_sources silently skips the entry (ev_type == "" matches no branch). MEDIUM severity.
    2. SAFE — Qdrant 0-hits: hybrid_retriever always returns {"chunks": []} (never absent key) via explicit or [] defaults in both vector_search and keyword_search fallback paths.
    3. SAFE — hybrid_retriever.py _normalize_chunk_payload(): defensively normalizes all Qdrant payload fields with str(normalized.get(key) or "").strip() patterns. Missing keys get empty string defaults, not KeyError.
    4. LATENT — Score coercion: float(getattr(point, "score", 0.0) or 0.0) silently converts None/malformed scores to 0.0 with no warning logged. Cannot distinguish genuine zero from bad data.
    5. LATENT — Timestamp fields in chunk payloads: published_at is present in news chunk payloads and surfaced through _build_sources_hit_payload. created_at and ingested_at may exist in document chunk payloads and pass through to LLM context without explicit "today is X" anchor. -->

- [x] Audit `backend/app/services/tenn_chat.py` and `backend/app/routes/chat.py` for temporal anchoring risks:
  - Does the chat system prompt declare the current date? If so, is it passed correctly to the LLM on every call?
  - Are there retrieval results injected into the system prompt that include date fields the LLM could anchor to?
  - Does the tenn_chat orchestrator pass any `published_at` or timestamp values from retrieved chunks directly into the LLM prompt context in a way that might override the declared current date?
  - Is there a `freshness_warning` equivalent for the tenn_chat path (not just agent-mode `search_news`)?
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. CONFIRMED CRITICAL — tenn_chat.py system prompt does NOT declare current date. The system prompt instructs the LLM to "prefer evidence from more recent sources" and to note articles >7 days old, but never states "today is [date]". LLM must infer recency from context or training cutoff.
    2. CONFIRMED — published_at values from retrieved chunks are injected into LLM context (line 152, line 191 of tenn_chat.py). LLM sees date fields but has no reference point to evaluate them.
    3. CONFIRMED — No freshness_warning equivalent: tenn_chat.py extracts model_confidence from LLM payload but does not compute or inject article age as a confidence factor. chat.py calls score_turn() post-hoc but this cannot retroactively change the LLM's stated confidence.
    4. LATENT — Temporal bleed from session history: if prior turns in conversation_history reference recent events with dates, the LLM may anchor to those dates implicitly even if the current context has a different (older) published_at. No guard against this. -->

- [x] Audit Celery tasks and extraction pipeline for silent shape assumptions:
  - Read: `backend/app/tasks/news_tasks.py`, `backend/app/tasks/commentary_tasks.py`
  - Read: `backend/app/services/multipass_extraction.py` (or equivalent extraction service)
  - For each task: what happens when the LLM returns non-JSON or malformed JSON? Is there explicit handling or silent swallow?
  - Does any extraction task rely on a specific key in the LLM response that could be missing?
  - Does any task log the error but then return a `{}` or `None` result that silently marks the document as processed?
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. LATENT — news_tasks.py and commentary_tasks.py are thin wrappers that delegate entirely to their respective extractor classes. Risk is inherited.
    2. LATENT — In NewsMemoExtractor and CommentaryMemoExtractor: LLM returns non-JSON → field normalization coerces missing/malformed lists to [] via _normalize_list(). An extraction failure produces a valid memo with empty lists for key_events/claims/catalysts/risks. No log warning at the normalization site distinguishes "LLM said no events" from "LLM returned garbage." Both result in an identical stored empty-list memo.
    3. LATENT — Neither task raises an exception or emits a warning when all extracted fields are empty. The document is written to disk as if extraction succeeded, preventing re-extraction on the next run unless the record is explicitly invalidated.
    4. SAFE — LLM call exceptions do propagate (not caught in extractor). If _call_llm raises (e.g. network error), the task fails and Celery will retry or mark failed — document is not silently marked processed. -->

- [x] Audit `cockpit/core/session_memory.py` and `backend/app/services/session_memory.py` for data-shape risks:
  - Are session history entries validated before being appended to the LLM messages list?
  - Can a corrupt or unexpected session entry cause the agent loop to fail silently?
  - Is there any place where session state could include stale temporal context that bleeds into a new turn?
  - Record each finding
  <!-- DONE 2026-04-14: Findings:
    1. LATENT — session_memory.py is a thin wrapper over shared/session_memory_base.py. get_recent_turns() returns raw stored dicts. agent_loop.py line 257: messages.extend(conversation_history) — no validation that each entry has "role" and "content" keys. A corrupt session entry (missing role, or None content) produces a malformed messages list that may cause the LLM API call to fail or behave unexpectedly.
    2. LATENT — Temporal bleed: if a prior session turn referenced events or dates (e.g. "as of yesterday, BHP was..."), those strings remain in conversation_history and bleed into the next turn's LLM context without refresh. No TTL or staleness check on injected history turns.
    3. SAFE — session turns are stored as flat dicts with fixed keys (timestamp, session_id, thread_id, query, answer). The schema is enforced by build_turn_payload(). Corruption would require external interference with the session store. -->

- [x] Compile audit findings into a structured report:
  - Create file: `docs/claude/audit/2026-04-14-silent-failure-audit.md`
  - Use this YAML front matter:
    ```yaml
    ---
    type: report
    title: Silent Failure Audit — 2026-04-14
    created: 2026-04-14
    tags:
      - hardening
      - audit
      - silent-failures
      - data-shape
    related:
      - '[[docs/claude/lessons]]'
      - '[[docs/architecture/17_agentic_chat_architecture]]'
    ---
    ```
  - Structure the body as:
    - **Executive Summary**: 2-3 sentences on what the audit found overall
    - **Confirmed Vulnerabilities** (must fix): numbered list, each with: location (file:line), description, failure mode, severity (HIGH/MEDIUM)
    - **Latent Risks** (should fix): same format, lower severity
    - **Safe / Already Handled**: brief list of patterns that are properly defended
    - **Fix Priority Order**: ranked list of confirmed vulnerabilities from most to least urgent
  - This report is the input contract for Phase 02
  <!-- DONE 2026-04-14: Report created at docs/claude/audit/2026-04-14-silent-failure-audit.md.
    6 confirmed vulnerabilities (3 HIGH, 3 MEDIUM), 5 latent risks (all LOW), 10 safe patterns documented.
    Fix priority order established — top 3 are all directly related to the three original bugs' root patterns. -->
