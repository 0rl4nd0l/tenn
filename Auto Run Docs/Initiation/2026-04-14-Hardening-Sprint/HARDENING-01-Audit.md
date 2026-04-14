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


- [ ] Audit `cockpit/core/agent_loop.py` for silent shape assumptions in the main loop:
  - Read the full file: `financial-engine_v2/cockpit/core/agent_loop.py`
  - What happens when a tool result `dict` has a `None` value for a key the loop accesses directly?
  - Does `evidence.append(...)` guard against non-dict tool results?
  - Does the `tool_calls` multi-call branch guard against missing `id`, `tool`, or `arguments` keys in each call dict?
  - What happens if `on_thinking` is called with a `None` assessment or plan?
  - What happens when `_finalize_result` is called but `AgentResult.evidence` contains entries from mixed formats (orchestrator vs agent-loop)?
  - Trace what `routing_metadata` looks like when the HybridRouter selects cloud vs local — are there shape differences between cloud and local response metadata?
  - Record each finding

- [ ] Audit `cockpit/core/tool_executor.py` and `cockpit/core/tools.py` for tool executor shape contract violations:
  - Read: `financial-engine_v2/cockpit/core/tool_executor.py` — this is where `_exec_search_news` (line ~292) and `freshness_warning` injection live
  - Read: `financial-engine_v2/cockpit/core/tools.py` — this is where `gather_local_context` lives
  - For each tool handler, check: what does it return when the backend returns an unexpected shape (e.g. `null` instead of `{hits: [...]}`, a list instead of a dict, or a missing key)?
  - Does `_exec_search_news` add `freshness_warning` consistently for *all* result shapes, including when the backend returns 0 hits? (The current fix only fires when `hits` is non-empty — check the 0-hits path)
  - Does `gather_local_context` produce the same key shape when called via the local path vs cloud path?
  - For tool handlers that call external HTTP endpoints, does the error branch return a dict that the agent loop can still extract a `result` from?
  - Record each finding

- [ ] Audit `_build_ui_sources` in `backend/app/routes/cockpit_api.py` for remaining gaps:
  - Which tool names in the agent evidence branch are currently handled? (`search_news`, `gather_local_context`, `query_ticker_data`)
  - List all tool names registered in `cockpit/core/tools.py` or `cockpit/core/tool_definitions.py`
  - For each tool not currently handled in `_build_ui_sources`, what shape does its `result` dict have?
  - Could any unhandled tool return evidence that a user would want to see in the sources panel?
  - Does the orchestrator-format branch handle every `ev_type` that the backend actually emits? Check `retrieval_orchestrator.py` for all `type` values it can produce
  - Record each finding

- [ ] Audit `backend/app/services/retrieval_orchestrator.py` and `backend/app/services/hybrid_retriever.py` for shape contract violations:
  - Read both files (search first for the most relevant functions, then read selectively)
  - Does the orchestrator always produce evidence entries with a `type` key? Are there code paths where type is absent or `None`?
  - What does the orchestrator return when Qdrant returns 0 hits? Is there a `hits: []` or is the key absent entirely?
  - Does `hybrid_retriever.py` guard against Qdrant returning payloads without expected keys (e.g. `source_id`, `score`, `title`)?
  - Are there date/timestamp fields in retrieval results that the LLM could anchor "today" to? (Beyond `published_at` in news — check `created_at`, `updated_at`, `ingested_at` fields in any chunk payload)
  - Record each finding

- [ ] Audit `backend/app/services/tenn_chat.py` and `backend/app/routes/chat.py` for temporal anchoring risks:
  - Does the chat system prompt declare the current date? If so, is it passed correctly to the LLM on every call?
  - Are there retrieval results injected into the system prompt that include date fields the LLM could anchor to?
  - Does the tenn_chat orchestrator pass any `published_at` or timestamp values from retrieved chunks directly into the LLM prompt context in a way that might override the declared current date?
  - Is there a `freshness_warning` equivalent for the tenn_chat path (not just agent-mode `search_news`)?
  - Record each finding

- [ ] Audit Celery tasks and extraction pipeline for silent shape assumptions:
  - Read: `backend/app/tasks/news_tasks.py`, `backend/app/tasks/commentary_tasks.py`
  - Read: `backend/app/services/multipass_extraction.py` (or equivalent extraction service)
  - For each task: what happens when the LLM returns non-JSON or malformed JSON? Is there explicit handling or silent swallow?
  - Does any extraction task rely on a specific key in the LLM response that could be missing?
  - Does any task log the error but then return a `{}` or `None` result that silently marks the document as processed?
  - Record each finding

- [ ] Audit `cockpit/core/session_memory.py` and `backend/app/services/session_memory.py` for data-shape risks:
  - Are session history entries validated before being appended to the LLM messages list?
  - Can a corrupt or unexpected session entry cause the agent loop to fail silently?
  - Is there any place where session state could include stale temporal context that bleeds into a new turn?
  - Record each finding

- [ ] Compile audit findings into a structured report:
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
