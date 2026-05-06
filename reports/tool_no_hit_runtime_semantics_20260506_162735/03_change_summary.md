# Change Summary

`financial-engine_v2/backend/app/routes/cockpit_api.py`

- Added helper source items for tool no-hit and runtime failure traces.
- Extended default source-label mapping for `tool_no_hit:*`,
  `financial_truth:no_hit:*`, and `runtime_failure:*`.
- Added no-hit/degraded handling for web evidence, `get_financials`,
  announcements, local context, dossier recall, deep research, web search/fetch,
  watchlist alerts, screeners, and TV indicators.
- Added routing-metadata label derivation from evidence payload metadata while
  ignoring tool-level `claim_verified`.
- Tightened the visible-source guard so no-hit/degraded operational traces cannot
  support polished financial claims, while successful screener rows keep prior
  behavior.

`financial-engine_v2/cockpit/core/tool_executor.py`

- Added `_annotate_result_semantics()` to attach existing evidence-state labels
  to read-only tool results.
- Preserved semantic metadata through truncation fallbacks.
- Preserved web fallback errors from `WebFetcher.search_and_fetch()`.

`financial-engine_v2/cockpit/core/agent_loop.py`

- Added evidence-state metadata merging into final agent-loop routing metadata.
- Direct command tool execution now carries evidence-state metadata when present.

`financial-engine_v2/cockpit/core/chat.py`

- Explicit web-search failures now return degraded evidence/routing metadata.

Tests:

- Added focused fixture tests for financial truth missing rows, web failure,
  deep research failure, partial evidence plus runtime failure, operational
  trace/no-hit, holdings/watchlist/screener behavior, tool executor metadata,
  and agent-loop final metadata propagation.
