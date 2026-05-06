# Existing Label Paths

## Context Reports Read

- `reports/a2m_news_trace_20260506_110151/`
- `reports/a2m_ticker_news_retrieval_selection_20260506_141455/`
- `reports/full_system_stocktake_20260505_152038/09A_source_label_integrity_report.md`
- `reports/full_system_stocktake_20260505_152038/06A_news_retrieval_trace.md`
- `reports/full_system_stocktake_20260505_152038/04A_memory_retrieval_risk_report.md`
- `reports/memory_first_batch_post_cleanup_verification_20260505_182316/`

## Existing Runtime Paths

`financial-engine_v2/backend/app/services/tenn_chat.py`

- Selects ticker-filtered news context for company chat.
- Builds `sources` from retrieved rows, local context, and supporting evidence.
- Previously did not consistently expose per-source evidence-role labels from Tenn chat results.

`financial-engine_v2/backend/app/routes/cockpit_api.py`

- Normalizes source payloads for Cockpit API responses and streaming metadata.
- Already contained a useful taxonomy surface. This task made fallback ordering and financial truth coverage stricter.

`financial-engine_v2/cockpit/core/agent_loop.py`

- Produces agent-loop responses when synthesis succeeds, times out, or fails.
- Timeout/failure paths now emit degraded runtime metadata.

`cockpit-ui/components/cockpit/chat/chat-screen.tsx`

- Normalizes analyst metadata received from backend payloads and SSE events.
- Now preserves source label counts, evidence labels, source coverage status, and per-source claim verification.

`cockpit-ui/components/cockpit/chat/terminal-message.tsx`

- Renders the answer trust/status label.
- Now renders role-aware labels instead of the vague generic source-backed label on the updated paths.

`cockpit-ui/components/cockpit/chat/sources-drawer.tsx`

- Inspected as a target UI surface.
- Not changed in this lane; source metadata is available for a future drawer-specific polish pass.

## Existing Correct Boundary

Holdings tests showed the intended local personal data boundary:

- holdings answers come from cockpit-local data
- holdings are not financial truth
- holdings are not external web/source-backed financial evidence

That behavior was preserved and covered by regression tests.
