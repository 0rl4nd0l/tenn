# Cockpit LLM Response Function Quality – Results & Evidence

Report from implementing the **Cockpit LLM Response Function Quality Analysis** plan.  
Date: 2026-03-01.

---

## 1) Test Results Summary

### Existing cockpit tests (all pass)

| Test file | Result | Notes |
|-----------|--------|--------|
| test_cockpit_action_intent_routing.py | OK (2 tests) | detect_action_intent routing |
| test_cockpit_chat_ticker_detection.py | OK (3 tests) | _detect_ticker |
| test_cockpit_deep_analysis_grounding.py | OK (12 tests) | echo, framework-only, contract, fallbacks |
| test_cockpit_announcement_sync_offer.py | OK (6 tests) | sync status, action preview |
| test_cockpit_access_request_triggers.py | OK (5 tests) | web/rag access preview, max-depth profile behavior |
| test_cockpit_price_history_chat.py | OK (4 tests) | historical price short-circuit |

**Commands used:**  
`cd financial-engine_v2 && python3 scripts/test_cockpit_*.py -v` (run each file directly with unittest).

### New unit tests (test_cockpit_llm_response_quality.py)

| Test class | Result | Notes |
|------------|--------|--------|
| TestMessageCap | OK (2) | Long message capped; COCKPIT_MAX_USER_MESSAGE_CHARS respected |
| TestPromptEchoDetection | OK (3) | _looks_like_prompt_echo true/false cases |
| TestVerificationDisclaimer | OK (3) | _has_verification_disclaimer |
| TestSanitizePromptPayload | OK (4) | docs/snippet limits, non-dict → empty |
| TestPromptConstruction | OK (1) | Prompt contains user question + Local evidence JSON |
| TestGatherContextTimeout | OK (1) | Timeout returns fallback payload with note=context_gather_timeout |

**Command:**  
`cd financial-engine_v2 && python3 scripts/test_cockpit_llm_response_quality.py -v`

---

## 2) Adversarial Test Runs (Evidence)

| Test name | Input | Data fixture | Expected | Observed | Pass |
|-----------|--------|--------------|----------|----------|------|
| ambiguous_query | "analyse" (no ticker) | any | Ask for ticker / specify ticker | "Please specify a ticker (for example: \`analyse BHP\`) so I can anchor the answer to real documents. If you want the index universe, ask: \`what tickers do you have announcements for\`." | Yes |
| data_empty (deep, web off) | "analyse XYZ" | docs=[], financials=[] | "Cannot be verified" or no-data message | In deep-context path with web disabled: short-circuit returns "Deep context can auto-run web enrichment... Use /confirm to approve". So user is prompted for web access before no-data message. | N/A (design: web offer first) |
| simple price query | "what is BHP price?" | price_state.ok=False | Graceful no-data or error | "This cannot be verified based on available data. Price feed error: price lookup failed" | Yes |
| long_input | 15k+ char message | — | No crash; message capped | build_chat_response completes; response contains LLM answer; message truncated to 8000 chars internally | Yes |
| context timeout | — | SlowRouter sleep 5s, timeout 1s | Fallback payload with context_gather_timeout | _gather_local_context_with_timeout returns ToolResult(ok=False, payload={"note": "context_gather_timeout", ...}); log: "gather_local_context timed out after 1s" | Yes |

---

## 3) Implemented Fixes (Deliverable 6)

| Fix | File | Change | Risk |
|-----|------|--------|------|
| **Fix 1 (S2)** | cockpit/core/chat.py | Cap user message: `message = (message or "")[:max(1, _max_user_chars)]` with `COCKPIT_MAX_USER_MESSAGE_CHARS` (default 8000) at start of `build_chat_response`. | Low |
| **Fix 2 (S2)** | cockpit/core/chat.py | After DATA INTEGRITY RULE: "When data_quality or financials are provided, explicitly note missing periods, duplicates, low-confidence rows, or extraction failures; do not smooth over gaps." | Low |
| **Fix 3 (S3)** | cockpit/core/chat.py | Before `ollama_client.chat`: `logging.getLogger(__name__).info("cockpit_llm_request mode=%s prompt_len=%d", mode, len(prompt_used))`. Added `import logging`. | Low |
| **Fix 4 (S3)** | cockpit/core/chat.py | `_gather_local_context_with_timeout(ticker, query, deep_mode)` runs `tool_router.gather_local_context` in `ThreadPoolExecutor` with `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS` (default 60). On `concurrent.futures.TimeoutError` returns `ToolResult(ok=False, payload={..., "note": "context_gather_timeout"})`. All 5 call sites use this helper. | Medium (timeout value/config) |

---

## 4) Issues Ranked (from plan Section 6; no new S0/S1)

- **S2** Message truncation → fixed (Fix 1).  
- **S2** Data-quality instruction → fixed (Fix 2).  
- **S2** Long LLM reply in operational mode → not changed (no max output length).  
- **S3** Nondeterminism (temperature, no seed) → not changed.  
- **S3** gather_local_context timeout → fixed (Fix 4).  
- **S3** Non-UTF-8 in message → not changed.

---

## 5) Regression / Confidence

- **Existing tests:** All 6 cockpit test files listed above pass after changes.  
- **New tests:** 14 tests in test_cockpit_llm_response_quality.py pass (message cap, prompt echo, verification disclaimer, sanitization, prompt construction, context timeout).  
- **Confidence:** High for routing, short-circuits, and new robustness (cap, timeout, logging). Conversational/truthfulness/data-reasoning still depend on LLM behavior; prompt and fallbacks improved by Fix 2 and existing contract/fallback logic.

---

## 6) How to Reproduce

```bash
cd financial-engine_v2
python3 scripts/test_cockpit_action_intent_routing.py -v
python3 scripts/test_cockpit_chat_ticker_detection.py -v
python3 scripts/test_cockpit_deep_analysis_grounding.py -v
python3 scripts/test_cockpit_announcement_sync_offer.py -v
python3 scripts/test_cockpit_access_request_triggers.py -v
python3 scripts/test_cockpit_price_history_chat.py -v
python3 scripts/test_cockpit_llm_response_quality.py -v
```
