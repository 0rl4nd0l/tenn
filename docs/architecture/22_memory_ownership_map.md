# Memory Ownership Map (Phase 0/1)

Last updated: 2026-04-21

| Surface | Logical role | Primary writers | Primary readers | Retention | Authority class |
|---|---|---|---|---|---|
| `asx_periodic_financials` (Postgres) | Canonical financial truth | Deterministic ingestion + extraction + normalization pipeline | Backend context APIs, query orchestrator financial truth provider | Durable | Authoritative truth |
| `reports/research_memory/company_memory.sqlite` | Company memory (qualitative, evidence-bound) | `memory_signal_router`, manual API (`/api/context/memory/company/*`) | Query orchestrator + `/api/context/memory` + `/api/context/company_dump` | Durable | Reasoning memory (non-numeric) |
| `reports/research_memory/market_memory.sqlite` | Market memory (sector/macro qualitative context) | `memory_signal_router`, manual API (`/api/context/memory/market/*`) | Query orchestrator + `/api/context/memory` + `/api/context/company_dump` | Durable | Reasoning memory (non-numeric) |
| `reports/research_memory/user_thesis_memory.sqlite` | User thesis memory (confirmation-gated) | Proposal API + explicit confirm + explicit apply (`/api/context/thesis/proposals*`) | Query orchestrator + `/api/context/thesis` + `/api/context/memory` + `/api/context/company_dump` | Durable | Reasoning memory (user-owned) |
| `~/.openviking/...` session store | Session/recency + semantic recall | Cockpit conversation/session layer | Cockpit chat loop | Medium-term | Working/session memory |
| `cockpit_state.db` | Operational state (jobs, watch tasks, UI state) | Cockpit runtime | Cockpit runtime/UI | Durable | Operational (not reasoning memory) |
| `reports/cockpit/feedback/*` + feedback tables | Feedback capture | Cockpit feedback capture flows | Cockpit feedback/triage flows | Durable | Operational feedback (not memory) |
| `reports/*`, `exports/*`, analyst notes | Workspace artifacts | Analysts/agents | Analysts/agents | Durable | Workspace/non-authoritative |
| Qdrant semantic stores (`asx_docs`, `news_chunks`, `commentary_chunks`) | Semantic retrieval aid | Ingestion/indexing pipelines | RAG query endpoints + contextual retrieval | Durable | Retrieval index (not truth memory) |

## Write Rules (implemented)
- Financial truth is not writable from LLM prose or qualitative memory APIs.
- Company/market memory reject financial metric signal types.
- User thesis memory writes are confirmation-gated through proposal -> confirm -> apply.
- Feedback remains outside reasoning memory surfaces.

## Read Rules (implemented)
- Query orchestrator now assembles memory via a deterministic `MemoryAssembler` contract.
- Source plan and selection are explicit per intent, with stale/weak filtering applied per source class.
- Read traces and write traces are emitted to:
  - `reports/research_memory/memory_read_events.jsonl`
  - `reports/research_memory/memory_write_events.jsonl`
