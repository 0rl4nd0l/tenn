# Chat Ticker Intent Misclassification Audit

Issue: #119

Mode: audit-only

Branch: `audit/chat-ticker-intent-misclassification-v1-20260602`

Worktree: `/home/l4nd0/tenn-chat-ticker-intent-misclassification-audit-v1-20260602`

## Summary

The #119 behavior is reproducible against current ticker-detection code without starting live services. The exact Gemini prompt includes the phrase `Cockpit UI`; the standalone uppercase token `UI` is not in ticker stopwords, and `detect_tickers(...)` returns uppercase candidates before whole-message or cue-pattern checks.

This explains how the prompt became ticker-scoped as `UI` and why the news no-hit/action-proposal path could offer `daily_news_ingest` for `UI`.

This task did not implement remediation. #119 should remain open.

## Files Inspected

- `financial-engine_v2/shared/ticker_inference.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/cockpit/tests/test_turn_continuity.py`
- `financial-engine_v2/cockpit/tests/test_tool_executor.py`
- `/home/l4nd0/.gemini/tmp/tenn-nvme-clean-baseline-reconstruct-v1/ui-audit-gemini-20260526/audit-results.json`

## Artifacts

- `ticker_probe.json`: deterministic probe results and source artifact summary.
- `root_cause.md`: root-cause classification and remediation guidance.
- `validation.json`: validation commands and results.
- `diff-check.json`: task-card diff allowlist result.

## Closeout Decision

`KEEP_OPEN`.

Reason: this audit documents root cause but does not add regression coverage or product remediation. The issue's acceptance criteria still require a separate implementation that preserves explicit ticker routing while preventing audit/session/UI acronyms from being treated as ticker scope.
