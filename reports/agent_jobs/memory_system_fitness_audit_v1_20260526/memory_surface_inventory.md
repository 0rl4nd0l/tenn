# Memory Surface Inventory

## Classification Summary

| Surface | Class | Primary store | Writers | Readers | Fitness |
|---|---|---|---|---|---|
| Canonical financial truth | Authoritative truth | Postgres `asx_periodic_financials` | deterministic ingestion/extraction/normalization | backend context APIs, query orchestrator financial-truth provider | Fit; must remain separate from memory |
| Company memory | Reasoning memory, non-numeric | `reports/research_memory/company_memory.sqlite` | `memory_signal_router`, manual backend APIs | query orchestrator, context memory APIs, company dump | Fit; needs broader fixture validation |
| Market memory | Reasoning memory, non-numeric | `reports/research_memory/market_memory.sqlite` | `memory_signal_router`, manual backend APIs | query orchestrator, context memory APIs, company dump | Fit; needs broader fixture validation |
| User thesis memory | User-owned reasoning memory | `reports/research_memory/user_thesis_memory.sqlite` | proposal API, explicit confirm, explicit apply | query orchestrator, thesis APIs, memory UI | Fit; confirmation gate is correct |
| OpenViking session memory | Working/session memory | `~/.openviking/...` | cockpit session layer | cockpit chat context | Adequate; live availability not verified |
| Cockpit StateStore | Operational state plus preferences | `~/.financial_engine_cockpit/state.db` | cockpit runtime/API | cockpit runtime/UI/system prompts | Mixed; preferences need clearer architecture inventory |
| MemoryStore filesystem | Workspace/research/session artifacts | `~/.tenn/memory/` | agent memory tools, compactor | agent loop/research workflows | Adequate; semantic recall and cleanup are limited |
| Company dossier | Workspace/research artifact | `~/.tenn/memory/dossiers/*.jsonl` | agent research tools | local context/dossier recall | Adequate; keyword-only recall is documented |
| Situation memory | Workspace/pattern memory | `~/.tenn/memory/situations.jsonl` | research workflows | explicit tool calls | Adequate; not standard answer context |
| Feedback and flagged reports | Operational feedback | feedback tables and `reports/cockpit/feedback/*` | feedback capture flows | cockpit feedback/triage flows | Fit as non-memory operational feedback |
| Marketplace tables | Operational/product state | cockpit SQLite tables | marketplace flows | marketplace APIs/UI | Fit as operational state, not financial truth |
| Qdrant stores | Retrieval index | `asx_docs`, `news_chunks`, `commentary_chunks` | ingestion/indexing pipelines | backend retrieval/RAG APIs | Fit; not truth memory |
| Reports, exports, analyst notes | Workspace artifacts | `reports/*`, `exports/*` | analysts/agents | analysts/agents | Fit as non-authoritative artifacts |

## Evidence Notes

- The ownership map lists the active surfaces and authority classes (`docs/architecture/22_memory_ownership_map.md:5`).
- Cockpit memory docs define six logical classes: canonical financial truth, company memory, market memory, user thesis memory, session memory, and operational/workspace state (`docs/architecture/18_cockpit_memory.md:11`).
- Backend memory classes are explicitly called authoritative for reasoning-memory surfaces, while operational state remains outside reasoning-memory authority (`docs/architecture/18_cockpit_memory.md:203`).
- StateStore includes `user_preferences`, session summaries, strategy, entity observations, jobs, watchlist, and chat messages (`docs/architecture/18_cockpit_memory.md:38`).
- MemoryStore is a filesystem tier with durable notes, sessions, research, and daily summaries (`docs/architecture/18_cockpit_memory.md:68`).

## Inventory Gaps

- Learned chat preferences in `financial-engine_v2/backend/app/services/chat_preferences.py` and `chat_preference_updater.py` are not fully modeled in `22_memory_ownership_map.md`.
- Live runtime memory root and active SQLite ownership were not verified to avoid write-prone imports or constructor side effects.
- UI coverage for memory management is documented and tested with mocks, but live route parity was not proven in this audit.
