# 18. Cockpit Memory System

> Canonical reference for how the cockpit persists and retrieves conversational, research, and strategic state across sessions.

---

## 1. Overview

The cockpit memory system gives Tenn cross-session continuity. Without it, every conversation starts from scratch: the LLM has no awareness of prior research, user preferences, or historical decisions.

As of 2026-04-21, memory is organized as explicit logical classes:

1. **Canonical financial truth** (deterministic financial facts only)
2. **Company memory** (durable qualitative company signals)
3. **Market memory** (durable qualitative sector/macro signals)
4. **User thesis memory** (durable but confirmation-gated user thesis/evidence)
5. **Session memory** (short-horizon continuity and semantic recall)
6. **Operational/workspace state** (jobs, alerts, feedback, drafts; not reasoning truth)

All memory is local-only. Nothing leaves the host machine. The storage layers range from ephemeral (active session turns) to permanent (watchlist, strategy, dossier), with cleanup policies that prevent unbounded growth in the SQLite tables.

The memory system operates on a **best-effort** principle: every memory read and write is wrapped in exception handlers so that a storage failure never blocks the primary chat response. This is by design -- memory enhances context but is not required for correctness.

Backend-owned qualitative memory remains authoritative. Cockpit may inspect and manage that memory only through backend APIs; it must not edit the backend SQLite stores directly.

For ownership and authority boundaries, see [22_memory_ownership_map.md](22_memory_ownership_map.md).

---

## 2. Storage Layers

### 2.1 StateStore (SQLite -- primary structured storage)

**File:** `financial-engine_v2/cockpit/storage/state.py`
**Location:** `~/.financial_engine_cockpit/state.db`
**Thread safety:** `threading.Lock` guards all writes; `check_same_thread=False` on the connection.

The StateStore is the cockpit's primary persistence layer. It manages 10 SQLite tables:

| Table | Schema | Purpose |
|-------|--------|---------|
| `chat_messages` | `id, thread_id, role, content, created_at` | Conversation history per thread |
| `jobs` | `job_id, action_id, args_json, started_at, ended_at, status, exit_code, stdout_path, stderr_path, artifacts_json` | Action execution log |
| `analysis_exports` | `id, thread_id, question, markdown_path, json_path, created_at` | Exported analysis artifacts |
| `watchlist` | `ticker (PK), added_at` | User's watched tickers |
| `update_events` | `id, thread_id, ticker, action_id, status, summary_json, created_at` | Ticker update audit trail |
| `entity_observations` | `id, ticker, observation_type, content, source, created_at` | LLM-extracted ticker facts |
| `user_preferences` | `key (PK), value, updated_at` | User settings (key-value) |
| `session_summaries` | `id, session_date, summary, tickers_mentioned, created_at` | Cross-session episodic memory |
| `global_strategy` | `id, criterion, category, priority, notes, created_at, updated_at` | Global investment criteria |
| `ticker_strategy` | `id, ticker, criterion, category, priority, decision, decision_rationale, notes, created_at, updated_at` | Per-ticker criteria and decisions |

**Read patterns:**
- Chat messages: fetched as the 12 most recent rows (DESC then reversed) for context injection. The `limit=12` is the agent loop default; keyword mode uses `limit=200` but only injects the last 6 turns.
- Entity observations: fetched per-ticker (limit 8) during `gather_local_context`.
- Session summaries: fetched at system prompt build time (limit 2).
- Preferences: fetched at system prompt build time.
- Watchlist: read on startup and by watchlist trigger.

**Write patterns:**
- Chat messages: written after every user message and every assistant response.
- Entity observations: written after every response that mentions a ticker, via rule-based extraction (`_extract_ticker_observations`).
- Session summaries: written at session end.
- Strategy: written via explicit user commands or agent tool calls.

**Cleanup:** `StateStore.cleanup()` is called at app startup (`ui/app.py` line 150). See section 6 for retention policy.

### 2.2 MemoryStore (filesystem -- tiered markdown)

**File:** `financial-engine_v2/cockpit/core/agent/memory/store.py`
**Root directory:** `~/.tenn/memory/`
**Thread safety:** None (single-writer design assumed).

A pure filesystem layer that stores agent memory as markdown and JSONL files in four tiers:

```
~/.tenn/memory/
  MEMORY.md                    # Durable: user prefs, key findings
  sessions/
    current.md                 # Active session turns (JSONL lines)
    YYYY-MM-DD-HH.md           # Archived session logs
  research/
    <TICKER>.md                # Per-ticker agent research notes
  daily/
    YYYY-MM-DD.md              # Compacted daily summaries
```

| Tier | File(s) | Read | Write |
|------|---------|------|-------|
| Session | `sessions/current.md` | Not read for LLM context directly; used by compactor | Appended after each agent turn |
| Research | `research/<TICKER>.md` | Read during agent loop when `self._memory.read_research(ticker)` is called; injected as "Prior Research for {ticker}" (capped at 4000 chars) | Written by agent tools during research workflows |
| Durable | `MEMORY.md` | Not currently injected into LLM context | Written by agent tools for long-term findings |
| Daily | `daily/YYYY-MM-DD.md` | Not currently injected into LLM context | Written by the MemoryCompactor during session compaction |

**Session rotation:** `rotate_session()` archives the current session file to `sessions/YYYY-MM-DD-HH.md` and clears `current.md`. Multiple rotations within the same hour append to the same archive file.

### 2.3 CompanyDossierService (JSONL -- per-ticker research)

**File:** `financial-engine_v2/cockpit/core/research/dossier.py`
**Location:** `~/.tenn/memory/dossiers/<TICKER>.jsonl`
**Thread safety:** Append-only file writes (safe for single writer).

Each JSONL line is a research finding:

```json
{
  "ticker": "BHP",
  "finding": "Revenue declined 8% YoY driven by lower iron ore prices",
  "source": "deep_research",
  "source_url": "https://...",
  "confidence": 0.85,
  "category": "revenue",
  "ts": "2026-03-28T10:30:00+00:00"
}
```

**Read:** `recall(ticker, query=None, limit=5)` returns the most recent findings, optionally filtered by keyword match across finding, category, and source fields. Called during `gather_local_context` -- findings are injected into the context payload as `dossier_findings` (limit 5).

**Write:** `save(ticker, finding, source, ...)` appends a new finding. Called by agent tools during research workflows (deep research, web research, dossier tool calls).

**Filtering:** Keyword-based only (substring match on `finding`, `category`, `source`). No semantic search. BM25 or vector search is planned but not implemented for dossier.

### 2.4 SituationMemory (JSONL + BM25 index)

**File:** `financial-engine_v2/cockpit/core/research/situation_memory.py`
**Location:** `~/.tenn/memory/situations.jsonl`
**Thread safety:** Append-only writes; in-memory BM25 index rebuilt on each write.

Stores `(situation, outcome)` pairs for pattern matching. Uses `rank_bm25` (BM25Okapi) when installed, falling back to simple keyword overlap scoring.

```json
{"situation": "Iron ore price dropped 15% in Q3", "outcome": "BHP shares fell 8% but recovered within 6 weeks"}
```

**Read:** `recall(current_situation, n=3)` returns the top-N most similar past situations by BM25 score. Not currently injected into the standard chat context assembly -- available for research tools to query explicitly.

**Write:** `add(situation, outcome)` appends a new entry and rebuilds the BM25 index.

**Index lifecycle:** The BM25 index is built in memory at startup (all entries loaded from JSONL) and rebuilt after each write. No persistence of the index itself.

### 2.5 AlertReader (JSONL -- watchlist scan alerts)

**File:** `financial-engine_v2/cockpit/core/research/alerts.py`
**Location:** `~/.tenn/memory/alerts/pending.jsonl`
**Thread safety:** Append-only writes for `write_alert`; full rewrite for `mark_seen`.

Alerts are produced by background watchlist scan tasks and consumed by the cockpit agent. Each alert:

```json
{
  "id": "a1b2c3d4e5f6",
  "ticker": "CSL",
  "type": "price_alert",
  "message": "CSL dropped 5% today",
  "data": {},
  "ts": "2026-03-28T10:30:00+00:00",
  "seen": false
}
```

**Read:** `get(since_hours=24, ticker=None)` returns alerts from the last N hours, optionally filtered by ticker. Available to agent tools; not automatically injected into chat context.

**Write:** `write_alert(...)` appends a new alert (called by background scanner). `mark_seen(alert_ids)` rewrites the file with `seen: true` on matched alerts.

### 2.6 Session Memory (OpenViking integration)

**File:** `financial-engine_v2/cockpit/core/session_memory.py`
**Thread safety:** Managed by OpenViking library.

An optional integration with the OpenViking session memory library. When `~/.openviking/ov.conf` exists and the `openviking` package is installed, this provides semantic search over prior conversation turns.

**Read:** `get_relevant_session_context(session_id, query, limit=3)` returns structured prior-turn records relevant to the current query. Injected into the keyword-mode LLM context as "Relevant prior session context".

**Write:** `record_turn(session_id, payload)` persists each conversation turn. Called after both agent and keyword mode responses.

**Degradation:** When OpenViking is unavailable, all functions return empty results. A single startup log line reports the status.

### 2.7 Memory Management Surfaces (Cockpit client over backend APIs)

There are now three operator-facing memory inspection and management surfaces inside Cockpit:

1. **Chat slash commands**
   - `/filestats <TICKER>` remains the broad per-ticker dump.
   - `/memory show <TICKER>` and `/memory raw <TICKER>` provide a memory-focused view.
   - `/memory add [company|market] <TICKER> <NOTE>` adds a manual qualitative note through the backend.
   - `/memory remove company <TICKER> <ENTRY_ID>` and `/memory remove market [sector|macro] <ENTRY_ID>` soft-expire backend qualitative memory rows.
2. **Textual Memory screen**
   - A dedicated Cockpit screen lets the user load a ticker, inspect company/market memory rows, add a manual note, and expire a selected active row.
3. **Web Memory tab (`cockpit-ui`, `:8081`)**
   - Route: `/memory` in the Next.js Cockpit UI.
   - Browser BFF routes under `cockpit-ui/app/api/cockpit/memory/*` proxy to backend-owned `/api/context/memory*`, `/api/context/thesis*`, and `/api/context/company_dump`.
   - UI capabilities:
     - level-specific subsections for `company`, `sector`, `macro`, and `strategy` memory
     - browse + search/filter over loaded memory rows
     - manual add for company/sector/macro notes and thesis proposals
     - row expiry for active qualitative entries
     - thesis proposal `confirm` / `reject` / `apply` actions
     - safe edit semantics for qualitative rows via explicit expire+replace (no in-place backend row mutation)
   - Context panels expose framework/strategy/company context so operators can inspect what Tenn may consume during reasoning.

These surfaces are clients only. They call backend context/memory endpoints through `BackendApiClient` and do not create a second memory authority.

### 2.8 Backend Memory Classes and Contracts (authoritative)

Backend memory classes are the authoritative reasoning-memory surfaces for Tenn:

| Class | Primary store | Write contract | Read contract |
|-------|---------------|----------------|---------------|
| Canonical financial truth | Postgres `asx_periodic_financials` | Deterministic ingestion/extraction/normalization only | Used for explicit numeric truth |
| Company memory | `reports/research_memory/company_memory.sqlite` | Evidence-bound qualitative signals only; financial-metric signal types rejected | Retrieved through orchestrator/memory APIs |
| Market memory | `reports/research_memory/market_memory.sqlite` | Evidence-bound qualitative sector/macro signals only; financial-metric signal types rejected | Retrieved through orchestrator/memory APIs |
| User thesis memory | `reports/research_memory/user_thesis_memory.sqlite` | Proposal -> confirm -> apply (confirmation-gated writes only) | Retrieved as confirmed thesis/evidence items |
| Session memory | OpenViking session store + cockpit recency history | Conversation turn recording | Optional continuity/semantic recall |

Operational state (jobs, alerts, feedback) and analyst workspace artifacts remain outside reasoning-memory authority.

---

## 3. Context Assembly Flow

Context assembly differs between agent mode (default, structured) and keyword mode (legacy).

### 3.0 Backend Memory Assembler (deterministic read contract)

`financial-engine_v2/backend/app/services/memory_assembler.py` is now the deterministic memory read contract used by `query_orchestrator.py`:

- input: mode, query, intent, entities, and explicit source plan
- sources: `financial_truth`, `company_memory`, `market_memory`, `user_thesis_memory`
- filtering: stale/low-score inactive qualitative items are filtered before answer-input synthesis
- traces: every assembly emits a read event to `reports/research_memory/memory_read_events.jsonl`

Write-side memory mutations emit write events to `reports/research_memory/memory_write_events.jsonl`.

### 3.1 Agent Mode Flow

```
User message
  |
  v
ChatController.build_chat_response()
  |-- Greeting short-circuit (regex match -> immediate return)
  |-- Ticker detection (_resolve_ticker_context)
  |-- Action keyword detection (deterministic, no LLM)
  |-- Chart intent short-circuit
  |-- Price history short-circuit
  |
  v (non-shortcircuited queries)
ChatController._run_agent_loop()
  |
  |-- Fetch conversation history from StateStore (12 messages, last 6 used)
  |-- Inject strategy criteria (StrategyService.build_context_block)
  |-- Inject research memory (MemoryStore.read_research, capped 4000 chars)
  |-- Augment user message with strategy + research blocks
  |
  v
AgentLoop.run()
  |-- Build system instruction:
  |     |-- Domain persona + communication style rules
  |     |-- User preferences (from StateStore)
  |     |-- Prior session summaries (2 most recent from StateStore)
  |     |-- Tool definitions (~2500 tokens)
  |-- Send to HybridRouter (local llama.cpp or Anthropic API)
  |-- Process tool calls iteratively (up to iteration cap)
  |-- Return final response
  |
  v
Post-response recording:
  |-- record_turn() -> OpenViking session memory
  |-- MemoryStore.append_session_turn() (user + assistant)
  |-- _extract_ticker_observations() -> StateStore entity_observations
```

### 3.2 Keyword Mode Flow

```
User message
  |
  v
ChatController.build_chat_response()
  |-- (same short-circuits as agent mode)
  |
  v (keyword router path)
ToolRouter.gather_local_context()
  |-- DB context: docs, financials, doc_snippets, extraction_failures
  |-- Price data: current price, price state, valuation multiples
  |-- RAG context: qual_context (company + news collections)
  |-- Agent memory: entity_observations (8 most recent per ticker)
  |-- Dossier findings: 5 most recent per ticker
  |-- Prior analysis export: most recent for this ticker
  |-- Data quality signals
  |
  v
_build_system_instruction()
  |-- Domain persona
  |-- User preferences
  |-- Prior session summaries (2 most recent)
  |
  v
Context injection into user message:
  |-- OpenViking relevant prior turns (3 max)
  |-- Recent conversation history (6 turns, 400 chars each)
  |-- Strategy criteria block
  |-- Financial narrative + valuation multiples
  |-- Agent memory observations
  |-- Prior export reference
  |-- Readable evidence section (docs, financials, price, qual context)
  |
  v
LLM call (Ollama/llama.cpp direct)
  |
  v
Post-response recording (same as agent mode)
```

### 3.3 What Reaches the LLM vs What Is Gathered But Not Used

| Data Source | Reaches LLM (Agent) | Reaches LLM (Keyword) |
|-------------|---------------------|----------------------|
| System persona | Yes (system prompt) | Yes (system prompt) |
| User preferences | Yes (system prompt) | Yes (system prompt) |
| Session summaries (2) | Yes (system prompt) | Yes (system prompt) |
| Tool definitions | Yes (system prompt, ~2500 tokens) | No |
| Conversation history (6 turns) | Yes (passed as `conversation_history`) | Yes (injected into user message) |
| Strategy criteria | Yes (appended to user message) | Yes (injected into evidence section) |
| Research notes (MemoryStore) | Yes (appended to user message, 4000 char cap) | No |
| OpenViking prior turns | No (agent uses conversation_history instead) | Yes (injected into user message) |
| Entity observations | No (gathered but not injected in agent path) | Yes (via `agent_memory` in evidence) |
| Dossier findings | No (gathered but not injected in agent path; available via tool call) | Yes (via `dossier_findings` in evidence) |
| Prior export reference | No | Yes (in evidence section) |
| Financial data | Via tool calls (agent fetches on demand) | Yes (pre-loaded in evidence) |
| Price data | Via tool calls | Yes (pre-loaded in evidence) |
| RAG context | Via tool calls | Yes (pre-loaded in evidence) |
| Situation memory | No (explicit tool calls only) | No |
| Alerts | No (explicit tool calls only) | No |

### 3.4 Token Budget (16K model)

Approximate token breakdown for a typical agent-mode turn:

| Component | Approximate tokens |
|-----------|-------------------|
| System instruction (persona, prefs, session summaries) | 500-800 |
| Tool definitions | ~2500 |
| Conversation history (6 turns x 400 chars) | 600-900 |
| User message + strategy block + research notes | 200-1500 |
| **Available for LLM response** | **~10,000-12,000** |

For keyword mode, the evidence section (docs, financials, price, qual context) can consume 2000-5000 tokens, reducing response budget further.

---

## 4. Session Lifecycle

### 4.1 Startup

1. `CockpitApp.__init__()` creates `StateStore(config["memory"]["state_db"])`.
2. `StateStore._init_schema()` creates all 9 tables (idempotent `CREATE TABLE IF NOT EXISTS`).
3. `StateStore.cleanup()` runs immediately -- ages out rows per retention policy (see section 6).
4. `ChatController.__init__()` initialises:
   - `_ov_session_id` (random UUID per process)
   - OpenViking session memory (`_log_startup_status()`)
   - `MemoryStore` (if injected via `memory_store` parameter)
   - `StrategyService` (wraps StateStore)
   - `CompanyDossierService` (JSONL-backed)
   - `AlertReader` (JSONL-backed)
5. If `COCKPIT_AGENT_MODE=structured` (default): AgentLoop, HybridRouter, ToolExecutor, and research services are initialised.

### 4.2 During Conversation

For each user message:

1. **Pre-LLM:** Ticker detection, short-circuit checks, context gathering.
2. **LLM call:** Context assembled and sent (see section 3).
3. **Post-LLM:**
   - Chat message stored in StateStore (user message + assistant response).
   - Turn recorded in OpenViking session memory.
   - Turn appended to MemoryStore session file.
   - Entity observations extracted and stored (up to 3 per turn, 300 char cap per observation).

### 4.3 Shutdown

Session summary generation is available via `StateStore.add_session_summary(summary, tickers)` but is not automatically triggered at cockpit shutdown. The summary must be generated explicitly (e.g., by a closing agent action or slash command).

`MemoryStore.rotate_session()` archives the current session file. This is triggered by the `MemoryCompactor` when session limits are exceeded, not at shutdown.

### 4.4 Session Compaction (MemoryCompactor)

**File:** `financial-engine_v2/cockpit/core/agent/memory/compaction.py`

When the active session exceeds configured limits:
- **MAX_TURNS = 40** conversation turns, or
- **MAX_CHARS = 24,000** total character count

The compactor:
1. Splits turns at the midpoint (oldest half vs newest half).
2. Summarises the oldest half via `summarize_fn` (or drops with a placeholder if no summarizer).
3. Writes the summary to `daily/YYYY-MM-DD.md`.
4. Archives the current session via `rotate_session()`.
5. Re-writes only the kept (newer) turns to a fresh `sessions/current.md`.

---

## 5. Ticker Intelligence Model

### 5.1 Two-Tier Architecture

Ticker intelligence is split into two tiers with distinct truth levels:

**Tier 1: Analysis Artifacts (ground truth)**
These are derived from the financial-engine backend pipeline and represent verified, structured data:
- `asx_periodic_financials` -- extracted financial metrics (revenue, EBIT, NPAT, etc.)
- `documents` -- ingested ASX announcements with metadata
- `extraction_runs` -- extraction audit trail with confidence scores
- Price data -- fetched from market data providers
- Valuation multiples -- computed from price + financials

**Tier 2: Qualitative Memory (agent observations)**
These are LLM-generated or user-provided, representing interpretive context:
- Entity observations (StateStore) -- rule-based extraction from chat responses
- Dossier findings (JSONL) -- agent research conclusions with confidence scores
- Research notes (MemoryStore) -- markdown research per ticker
- Strategy criteria and decisions -- user-defined investment framework

### 5.2 Precedence Rules

When data conflicts between tiers:
- **Tier 1 always wins.** Financial metrics from extraction are authoritative.
- **Tier 2 supplements but never overrides.** Observations and dossier findings provide qualitative colour.
- The system prompt explicitly instructs the LLM: "Never fabricate metrics not present in the evidence payload."

### 5.3 How Analysis Artifacts Integrate

During `gather_local_context`, the ToolRouter builds a comprehensive payload:
1. **Financials** from the backend database, plus a generated `financials_narrative` (trend summary).
2. **Valuation multiples** computed from the latest price and financial row.
3. **Price state** including trend regime, momentum, volatility, and drawdown metrics.
4. **Document snippets** from announcement context or live PDF extraction.
5. **RAG context** from Qdrant (company commentary + news collections).

These are assembled into readable text sections (not raw JSON) before injection into the LLM prompt.

### 5.4 Entity Observations: Role and Limitations

Entity observations are extracted after each LLM response using rule-based pattern matching (`_extract_ticker_observations`). The extractor matches sentences containing the ticker against a vocabulary of financial signal words across 8 categories: revenue, profitability, cashflow, debt, guidance, risk, catalyst, valuation.

**Current limitations:**
- **Circularity risk:** The LLM generates text, observations are extracted from that text, and those observations are fed back into future LLM context. If the LLM hallucinates a claim (e.g., "BHP revenue grew 20%"), it becomes a stored observation that reinforces the hallucination in future turns.
- **Cap of 3 observations per turn** mitigates noise but does not eliminate circularity.
- **300-character content cap** per observation.
- **30-day retention** provides natural decay, but stale observations can still mislead within that window.

---

## 6. Retention Policy

### 6.1 Permanent Storage (no automatic cleanup)

| Data | Location | Rationale |
|------|----------|-----------|
| Watchlist | `state.db / watchlist` | User-curated, small dataset |
| User preferences | `state.db / user_preferences` | Key-value, tiny |
| Global strategy | `state.db / global_strategy` | User-defined criteria |
| Ticker strategy | `state.db / ticker_strategy` | User-defined criteria + decisions |
| Analysis exports | `state.db / analysis_exports` | References to exported files |
| Dossier findings | `~/.tenn/memory/dossiers/*.jsonl` | Append-only research memory |
| Research notes | `~/.tenn/memory/research/*.md` | Per-ticker markdown |
| Durable memory | `~/.tenn/memory/MEMORY.md` | Agent long-term findings |
| Situation memory | `~/.tenn/memory/situations.jsonl` | Pattern library |

### 6.2 Time-Limited Storage (automatic cleanup at startup)

| Table | Retention | Column |
|-------|-----------|--------|
| `chat_messages` | 90 days | `created_at` |
| `entity_observations` | 30 days | `created_at` |
| `update_events` | 90 days | `created_at` |
| `jobs` | 90 days | `started_at` |
| `session_summaries` | 30 days | `created_at` |

### 6.3 Cleanup Mechanism

`StateStore.cleanup()` is called once at app startup. It iterates over the five time-limited tables, deletes rows older than the configured threshold, and logs the count of deleted rows per table. All deletions happen within a single lock acquisition and commit.

Alerts (`pending.jsonl`) are not cleaned up automatically. The `AlertReader.get()` method filters by `since_hours` at read time, so old alerts are ignored but not deleted.

MemoryStore session archives (`sessions/YYYY-MM-DD-HH.md`) and daily summaries (`daily/YYYY-MM-DD.md`) are never automatically deleted.

---

## 7. Known Limitations and Future Work

### 7.1 12-Message Context Window

The agent loop fetches the 12 most recent chat messages from StateStore but only uses the last 6 turns (after excluding the current message). This means the LLM has at most 6 prior exchanges of context. For long research sessions, earlier context is lost unless it was captured in session summaries, dossier findings, or research notes.

### 7.2 No Multi-Ticker Comparison in Keyword Mode

Keyword mode's `gather_local_context` loads data for a single ticker. There is no mechanism to load parallel context for multiple tickers in a single call. Agent mode can achieve multi-ticker context through sequential tool calls, but the keyword path cannot.

### 7.3 Tool Definition Token Cost

In agent mode, tool definitions consume approximately 2500 tokens of the context window. On a 16K model, this is 15% of total capacity. This cost is fixed regardless of whether tools are used in a given turn.

### 7.4 Entity Observation Circularity

As described in section 5.4, observations extracted from LLM-generated text can be fed back into future LLM context, creating a feedback loop. Mitigations (3-per-turn cap, 300-char limit, 30-day retention) reduce but do not eliminate this risk.

### 7.5 No Semantic Search for Dossier

Dossier recall uses substring matching. For tickers with many findings, relevant entries may not surface if the query terms do not overlap with the stored text. BM25-based retrieval (as used by SituationMemory) or vector search would improve recall quality.

### 7.6 No Semantic Index For MemoryStore

`MemoryStore` is currently a pure filesystem layer. Session logs, research notes, durable notes, and daily summaries are stored as markdown/JSONL files only; there is no semantic vector index over those files in the current runtime.

### 7.7 Session Summary Generation Not Automated

Session summaries must be generated explicitly. There is no automatic summarisation at cockpit shutdown, so cross-session context depends on manual or tool-triggered summary creation.

### 7.8 No Alert Cleanup

The `pending.jsonl` alert file grows indefinitely. Old alerts are filtered at read time but never deleted. A periodic cleanup mechanism (e.g., removing alerts older than 30 days) would prevent unbounded file growth.

---

## 8. File Reference Table

| File | Role | Lines |
|------|------|-------|
| `financial-engine_v2/cockpit/storage/state.py` | Primary SQLite store: 9 tables, CRUD, cleanup | 467 |
| `financial-engine_v2/cockpit/core/chat.py` | Context assembly, LLM dispatch, post-response recording | 1793 |
| `financial-engine_v2/cockpit/core/tools.py` | `gather_local_context`: builds the full evidence payload | 1320 |
| `financial-engine_v2/cockpit/core/strategy.py` | Strategy criteria and decisions; context block builder | 235 |
| `financial-engine_v2/cockpit/core/agent/memory/store.py` | MemoryStore: tiered markdown filesystem (session, research, durable, daily) | 181 |
| `financial-engine_v2/cockpit/core/agent/memory/compaction.py` | MemoryCompactor: session limit enforcement and archival | 116 |
| `financial-engine_v2/cockpit/core/session_memory.py` | OpenViking integration: semantic session search and turn recording | 159 |
| `financial-engine_v2/cockpit/core/research/dossier.py` | CompanyDossierService: JSONL per-ticker research memory | 171 |
| `financial-engine_v2/cockpit/core/research/situation_memory.py` | SituationMemory: BM25-indexed situation-outcome pairs | 149 |
| `financial-engine_v2/cockpit/core/research/alerts.py` | AlertReader: watchlist scan alert consumption | 131 |
| `financial-engine_v2/cockpit/core/agent_loop.py` | AgentLoop: structured tool-calling loop | 576 |
| `financial-engine_v2/backend/app/services/query_orchestrator.py` | Backend orchestrator: intent/source planning and answer-input composition across financial truth + memory classes | -- |
| `financial-engine_v2/backend/app/services/memory_assembler.py` | Deterministic memory read assembly and filtering + read event emission | -- |
| `financial-engine_v2/backend/app/services/user_thesis_memory.py` | Confirmation-gated user thesis proposal/confirm/apply storage and retrieval | -- |
| `financial-engine_v2/backend/app/services/memory_events.py` | Memory read/write event logging (`memory_read_events.jsonl`, `memory_write_events.jsonl`) | -- |
| `financial-engine_v2/backend/app/api/context.py` | `/api/context/memory*`, `/api/context/thesis*`, and memory-inclusive ticker/company dump routes | -- |
| `financial-engine_v2/cockpit/core/config.py` | Config defaults including `state_db` path | -- |
| `financial-engine_v2/cockpit/ui/app.py` | App startup: StateStore init, cleanup call | -- |
