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

# Silent Failure Audit — 2026-04-14

## Executive Summary

Systematic audit of the full stack following three confirmed production bugs (raw JSON leak, empty sources panel, stale-news temporal anchoring). Eleven confirmed or latent vulnerabilities found across six subsystems. The dominant failure mode is **unguarded shape assumptions at component boundaries** — particularly the agent-loop evidence format vs. orchestrator format duality — which leaves many tool results invisible in the UI and opens temporal anchoring gaps in both agent and non-agent chat paths. Two critical vulnerabilities require immediate attention: (1) `_exec_search_news` does not emit `freshness_warning` when the news corpus returns 0 hits, and (2) `tenn_chat.py` never declares today's date in its system prompt, leaving the LLM to infer recency from `published_at` fields without a reference point.

---

## Confirmed Vulnerabilities (must fix)

### 1. `_exec_search_news` — missing freshness_warning on 0-hit path
**Location:** `cockpit/core/tool_executor.py:373`
**Description:** The `freshness_warning` field is only computed when `compact_hits` is non-empty (line 374: `if compact_hits:`). When the backend returns 0 hits, the LLM receives no signal that the news corpus may be stale or absent. The LLM may present "no news" as factually current rather than as a corpus limitation.
**Failure mode:** LLM responds "there is no recent news on X" when the actual root cause is an unpopulated or stale corpus — presenting absence of data as a confirmed factual state.
**Severity:** HIGH

### 2. `tenn_chat.py` — no current date in system prompt
**Location:** `backend/app/services/tenn_chat.py` (system prompt construction, approx. lines 243–273)
**Description:** The system prompt instructs the LLM to "prefer evidence from more recent sources" and to note articles more than 7 days old, but never declares the actual current date. The LLM sees `"published_at": "2024-10-15"` fields and must infer recency relative to an unstated reference point.
**Failure mode:** LLM cannot compute "7 days old" without knowing today's date; it uses training cutoff or publication patterns as an implicit reference, producing incorrect recency assessments and false confidence on stale data.
**Severity:** HIGH

### 3. `_build_ui_sources` — thirteen tool result types silently dropped
**Location:** `backend/app/routes/cockpit_api.py:467–502`
**Description:** The agent-evidence branch (when `ev.get("tool") and not ev.get("type")`) only handles three tool names: `search_news`, `gather_local_context`, `query_ticker_data`. Tool definitions register 18 read-only tools. The following produce user-relevant evidence that is silently discarded: `search_announcements`, `get_financials`, `recall_dossier`, `deep_research`, `search_web`, `fetch_url`, `get_data_quality`, `run_analysis`, `get_price`, `get_price_on_date`, `get_price_range`, `search_social`, `get_watchlist_alerts`.
**Failure mode:** User sees empty Sources panel for any query that exercised one of these tools, even when the tool returned substantive results. The evidence exists in the `AgentResult` but is invisible to the UI.
**Severity:** HIGH

### 4. `_repair_json` — cannot repair unterminated strings or mismatched delimiters
**Location:** `cockpit/core/response_parser.py:67–76`
**Description:** `_repair_json` only removes trailing commas. It does not handle unterminated strings, mismatched `{` / `}` / `[` / `]`, or escaped quote sequences. If the LLM truncates its output mid-string (e.g. context window overflow), the repair step provides no help.
**Failure mode:** Truncated LLM responses fall through to the plain-text fallback, losing all structured metadata (tool name, arguments) and appearing to the user as if the LLM gave a non-answer.
**Severity:** MEDIUM

### 5. `tenn_chat.py` — no freshness_warning equivalent for non-agent chat
**Location:** `backend/app/services/tenn_chat.py` (confidence scoring path)
**Description:** The agent path (`_exec_search_news`) now emits `freshness_warning` when articles are ≥2 days old. The `tenn_chat` path has no equivalent: it extracts `model_confidence` from the LLM payload but does not penalize confidence based on the age of retrieved articles. The `chat.py` route calls `score_turn()` after the LLM has already committed to its confidence value.
**Failure mode:** LLM returns `"confidence": 0.8` on 10-day-old data in the non-agent chat path with no warning to the user, while identical data in agent mode would carry a staleness caveat.
**Severity:** MEDIUM

### 6. `retrieval_orchestrator.py` — evidence entries may lack `type` key
**Location:** `backend/app/services/retrieval_orchestrator.py` (evidence assembly, approx. lines 132–153 and 192–200)
**Description:** Commentary chunks retrieved from `commentary_retriever.retrieve()` are assembled into evidence entries without explicitly setting a `type` key. If the retriever's payload does not include `type`, downstream consumers that rely on `ev.get("type")` in `_build_ui_sources` will silently skip the entry (falling into the `ev_type == ""` case, which matches nothing).
**Failure mode:** Commentary evidence is fetched, passed through the full pipeline, and then silently dropped at the UI sources layer.
**Severity:** MEDIUM

---

## Latent Risks (should fix)

### 7. `_try_split_multi_json` — third object (tool_call type) in multi-object completion is silently skipped
**Location:** `cockpit/core/response_parser.py:206–236`
**Description:** When the LLM emits three concatenated objects (e.g. `{thinking}{tool_call}{response}`), the multi-object parser iterates all three and correctly finds the `response` object. However, if the LLM emits `{thinking}{response}{response}` (two response objects), only the most-recently-scanned one is used (last-write wins on `response_obj`). Also, any non-thinking non-response objects (e.g. a stray `tool_call` in a multi-object completion) are silently ignored without a log entry.
**Failure mode:** Rare; would only trigger if the LLM emits an unusual multi-object sequence. Silent loss of intermediate structured objects.
**Severity:** LOW (currently, LATENT)

### 8. `_infer_type` — ambiguous when both `tool` and `assessment` keys are present
**Location:** `cockpit/core/response_parser.py:140–151`
**Description:** `_infer_type` checks `assessment in obj` before `tool in obj`. If an LLM emits an object with both `assessment` and `tool` keys (e.g. a confused partial merge of thinking and tool_call), it will be inferred as `"thinking"` and the `tool` key will be ignored.
**Failure mode:** Rare hybrid LLM output would be silently re-typed as thinking, discarding tool intent.
**Severity:** LOW (currently, LATENT)

### 9. `_exec_query_ticker_data` — unsafe spread of ToolResult.payload
**Location:** `cockpit/core/tool_executor.py:139–145`
**Description:** After calling `self._router.gather_local_context(...)`, the code extracts `result.payload` (defaulting to `{}`). It then spreads `**payload` directly into the return dict. If `payload` is not a dict (e.g. if `gather_local_context` returns a non-standard ToolResult implementation), this `**` spread raises a `TypeError`.
**Failure mode:** Tool executor's outer `try/except` at line 100 would catch this and return `{"ok": False, "error": "Tool execution failed: ..."}`, but the error would not indicate a shape contract violation — it would look like a tool failure.
**Severity:** LOW (LATENT — currently both code paths produce dicts)

### 10. `hybrid_retriever.py` — silent score coercion masks malformed Qdrant data
**Location:** `backend/app/services/hybrid_retriever.py:508`
**Description:** `normalized["vector_score"] = float(getattr(point, "score", 0.0) or 0.0)` silently coerces `None`, non-numeric strings, and other unexpected score values to `0.0`. Callers cannot distinguish a genuine zero score from a malformed/absent score. No warning is logged.
**Failure mode:** Incorrect ranking of retrieval results if Qdrant returns unexpected score formats. Silent data quality degradation.
**Severity:** LOW (LATENT)

### 11. `session_memory.py` — no shape validation on session turn entries before LLM injection
**Location:** `cockpit/core/session_memory.py` / `shared/session_memory_base.py`
**Description:** `get_recent_turns()` and `get_relevant_session_context()` return raw stored dicts. The agent loop appends these to `conversation_history` without validating that each entry has the required `role` and `content` keys (as expected by `_call_llm`). A corrupt or missing-key session entry would produce a malformed message list.
**Failure mode:** LLM API call may fail or produce unexpected behavior if a session entry lacks `role` or `content`. No guard at the injection site (agent_loop.py line 257: `messages.extend(conversation_history)`).
**Severity:** LOW (LATENT — requires corrupt session storage to trigger)

---

## Safe / Already Handled

- **Multi-JSON split handles arrays:** `_try_split_multi_json` scans for `{` / `}` pairs; inner objects within a top-level JSON array are correctly extracted as separate candidates.
- **`on_thinking` null safety:** `assessment = parsed.assessment or parsed.content or ""` and `plan = parsed.plan or ""` ensure neither is None before the callback.
- **Evidence always dict:** `_execute_tool` (agent_loop.py:836) wraps non-dict tool results in `{"result": result}` before appending to evidence.
- **`_normalize_tool_calls` missing-key safety:** Uses `.get("tool", "unknown")` and `.get("arguments") or {}` — no KeyError possible from tool_calls list entries.
- **`hybrid_retriever.py` zero-hits:** Always returns `{"chunks": []}`, never an absent key.
- **`_exec_get_company_dump` shape validation:** Explicitly checks `not isinstance(payload, dict)` before spread.
- **Tool executor outer exception guard:** All tool handler exceptions caught at `execute()` level, returned as structured error dicts, not raised.
- **`_build_ui_sources` non-dict evidence guard:** Line 345 filters `if not isinstance(ev, dict): continue`.
- **`_repair_json` trailing comma handling:** Correctly handles the most common LLM JSON malformation.
- **`_exec_search_news` non-dict result guard:** Line 306 checks `not isinstance(result, dict)` before key access.

---

## Fix Priority Order

1. **[HIGH] `_exec_search_news` 0-hit freshness_warning** — Directly extends the fix for Bug 3. One-line change with immediate staleness safety improvement.
2. **[HIGH] `tenn_chat.py` current date injection** — Closes the temporal anchoring gap in non-agent chat. Mirror of what the agent path already has via `freshness_warning`.
3. **[HIGH] `_build_ui_sources` unhandled tool names** — Sources panel will be empty for any query using 13 of 18 tools. High user-facing impact. Fix by adding result-shape extractors for at minimum: `search_announcements`, `recall_dossier`, `deep_research`, `search_web`, `get_financials`.
4. **[MEDIUM] `retrieval_orchestrator.py` missing `type` key** — Commentary evidence silently dropped. Add explicit `type` key setting when assembling evidence entries.
5. **[MEDIUM] `tenn_chat.py` freshness_warning for non-agent path** — Closes the confidence-staleness gap. Lower urgency than date injection but same root cause.
6. **[MEDIUM] `_repair_json` unterminated string handling** — Defensive improvement for edge-case LLM truncation. Does not affect normal operation.
7. **[LOW] `session_memory` validation** — Low probability trigger, low user-visible impact. Add `isinstance(entry, dict) and "role" in entry` guard at history injection.
8. **[LOW] Score coercion logging** — Add `logger.warning` when `point.score` is non-numeric. No behavioral change, improves observability.
9. **[LOW] `_infer_type` ambiguity** — Add explicit handling for objects with both `tool` and `assessment` keys. Cosmetic risk only.
10. **[LOW] `_exec_query_ticker_data` payload spread** — Validate `isinstance(payload, dict)` before `**payload` spread.

---

*This report is the input contract for Phase 02 — each Confirmed Vulnerability in sections 1–6 maps to a required fix in the Phase 02 fix list.*
