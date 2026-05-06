# Next Codex Prompt: Legacy API Chat Audit

Use this prompt for the next lane after G003:

```text
Lane: Query Orchestration
Execution mode: AUDIT MODE first, SAFE EXTENSION MODE only after preflight

Audit legacy `/api/chat` and `/chat` taxonomy handling without touching Textual `/sources`, source drawer UI, retrieval ranking, ingestion, Qdrant, news.sqlite, memory stores, or financial truth extraction.

Inspect:
- docs/architecture/SYSTEM_CONTRACT.md
- docs/architecture/21_cockpit_client_contract.md
- reports/textual_sources_list_envelope_consumption_20260506_172946/
- reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/04_legacy_api_chat_audit.md
- financial-engine_v2/backend/app/routes/chat.py
- financial-engine_v2/backend/app/services/tenn_chat.py
- financial-engine_v2/backend/tests/test_chat_route.py
- financial-engine_v2/backend/tests/test_sources.py

Question:
Does legacy `/api/chat` expose enough source-label taxonomy metadata for callers to avoid treating no-hit, degraded, context-only, memory, holdings, local news, web, and financial truth roles as generic source-backed evidence?

Hard stops:
- Do not break response shape for legacy clients.
- Do not touch source drawer UI.
- Do not mutate DB/Qdrant/news/memory.
- Do not change retrieval ranking.
- Do not rewrite synthesis prompts broadly.

Output:
- audit report
- proposed safe additive payload contract if needed
- focused tests if implementation is safe
```
