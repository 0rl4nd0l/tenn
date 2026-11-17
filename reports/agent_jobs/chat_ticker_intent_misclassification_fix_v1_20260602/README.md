# Chat Ticker Intent Misclassification Fix

Issue: #119

Mode: safe extension

Branch: `safe/chat-ticker-intent-misclassification-fix-v1-20260602`

Worktree: `/home/l4nd0/tenn-chat-ticker-intent-misclassification-fix-v1-20260602`

## Summary

The shared ticker detector no longer accepts every standalone uppercase token in ordinary prose. It now preserves explicit ticker forms and whole-message ticker requests, keeps compact uppercase ticker lists such as `BHP CSL RIO`, and otherwise relies on contextual cue patterns. Financial-fact `what were/is/are TICKER ...` cues are limited to financial terms so generic abbreviations such as `CI` are not promoted to tickers.

The exact Gemini audit prompt from #119 no longer resolves to ticker `UI`, including the `Cockpit UI` phrase that caused the failure. Audit marker variants embedded in prose also remain tickerless.

## Changed Files

- `financial-engine_v2/shared/ticker_inference.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/cockpit/tests/test_tool_executor.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `docs/agent_tasks/chat_ticker_intent_misclassification_fix_v1_20260602.md`
- `reports/agent_jobs/chat_ticker_intent_misclassification_fix_v1_20260602/*`

## Behavior Covered

- Exact Gemini prompt: tickerless.
- `UI AUDIT GEMINI ...` and punctuation-separated marker variants in prose: tickerless.
- `from Cockpit UI ...`: tickerless.
- `what are CI checks doing`: tickerless.
- `BHP news`, `tell me about csl`, `Summarize BHP in one sentence`, `What were BHP operating cash flows?`, and `why did BHP fall today`: still ticker-scoped.
- `ASX:UI news`, `$UI news`, and `UI.AX news`: still explicitly ticker-scoped.
- `BHP CSL RIO`: still detected as a compact ticker list.

## Boundaries

No runtime services were started. No browser replay, ingestion, action execution, DB, Qdrant, news, memory, financial-truth, parser, extraction, model, GPU, or service-config mutation was performed.

## Closeout Decision

`ROOT_CAUSE_FIXED_PENDING_PR`.

Issue #119 can close after this PR is visible, checks pass, and the issue comment links the fix evidence.
