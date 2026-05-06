# Summary

Lane: Query Orchestration
Supporting lane: Provenance
Execution mode: SAFE EXTENSION MODE
Collision risk: MEDIUM

Decision: proceed.

G008 status: fixed for Cockpit chat/API source extraction and tool-result
metadata paths covered by fixtures.

G009 status: fixed for web search/fetch, deep research, tool executor failures,
agent-loop routing metadata propagation, and explicit web-search shortcut
failures covered by fixtures.

No ingestion, Qdrant mutation, `news.sqlite` mutation, memory mutation, financial
truth extraction change, or retrieval-ranking change was performed.

Files changed:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/cockpit/tests/test_tool_executor.py`
- `financial-engine_v2/cockpit/tests/test_agent_loop.py`
- `reports/tool_no_hit_runtime_semantics_20260506_162735/*`

Unrelated dirty files were intentionally not touched. Current dirty state also
contains unrelated Cockpit UI files and `tenn_prompt_contracts_response_guidelines.zip`.
