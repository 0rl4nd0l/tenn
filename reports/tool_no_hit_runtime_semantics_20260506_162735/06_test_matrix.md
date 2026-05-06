# Test Matrix

Non-news no-hit source:

- `test_agent_format_get_financials_zero_rows_emits_missing_evidence`
- `test_agent_format_get_watchlist_alerts_without_rows_still_emits_source_item`
- `test_agent_format_tv_screener_without_rows_still_emits_source_item`
- `test_operational_no_hit_trace_is_not_financial_evidence`

Financial truth missing:

- `test_agent_format_get_financials_zero_rows_emits_missing_evidence`
- `test_cockpit_chat_stream_financial_truth_missing_rows_surfaces_missing_evidence`
- `TestGetFinancials.test_empty_backend_financial_rows_are_no_data_not_tool_failure`

Web/deep/runtime failure:

- `test_agent_format_search_web_failure_is_degraded_runtime`
- `test_agent_format_deep_research_failure_is_degraded_runtime`
- `test_cockpit_chat_stream_web_tool_failure_surfaces_degraded_runtime`
- `TestWebRuntimeSemantics.test_exec_search_web_fallback_preserves_failure_metadata`
- `TestWebRuntimeSemantics.test_exec_deep_research_failure_is_degraded_runtime`
- `test_degraded_tool_result_is_reflected_in_final_routing_metadata`

Partial evidence plus runtime failure:

- `test_partial_evidence_with_runtime_failure_keeps_evidence_and_degradation`

Operational trace:

- `test_operational_no_hit_trace_is_not_financial_evidence`

A2M/local-news:

- Existing A2M/local-news and source-label tests in
  `test_build_ui_sources.py`, `test_cockpit_api_chat_stream.py`, and the broader
  selector.

Holdings:

- `test_holdings_evidence_does_not_render_visible_sources`
- Existing Cockpit chat-stream holdings selector coverage.

Memory:

- `test_memory_source_is_context_not_claim_verified_financial_truth`
- Existing broader memory selector coverage.

Attached source:

- `test_attached_source_is_emitted_as_context_only_not_claim_verified`
- Existing broader attached-source selector coverage.
