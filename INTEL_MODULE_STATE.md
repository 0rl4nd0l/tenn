# Intel Module State — 2026-03-27

## 1. Risk Module

### What's built

**Single live pipeline (Postgres-based, synchronous at ingestion):**

- **Pass 3b** of multipass extraction generates narrative risk data via LLM call (`temperature=0`, deterministic)
- Fields written to `asx_risk_notes`: `risk_summary`, `risk_bullets`, `guidance_summary`, `material_changes`, `confidence_narrative`
- `PROMPT_HASH` correctly imported from `multipass_extraction.py` (SHA-256 of concatenated prompts, truncated to 16 chars)
- `EXTRACTOR_VERSION = "docling_multipass_v1"`

**Two API endpoints serve risk data:**

| Endpoint | Source | LLM calls | Auth |
|----------|--------|-----------|------|
| `GET /api/risk?document_id=` | `asx_risk_notes` table directly | None | None |
| `GET /api/analysis/risk?ticker=` | `risk_module.py` aggregation | None | API key required |

**Deterministic post-processing in `risk_module.py`:**

- Four regex-based risk categories: `operational`, `financial`, `regulatory`, `macro`
- Severity estimation via keyword matching: `high` / `medium` / `low`
- Aggregates: risk notes + RAG evidence from `asx_docs` + optional news context
- No LLM calls at query time — purely deterministic

**Financial metrics computed on-demand in `financial_metrics.py`:**

- Derived: `fcf`, `ebit_margin`, `np_margin`, `fcf_margin`, `cash_conversion`
- YoY deltas: `revenue_yoy`, `ebit_yoy`, `np_yoy`, `fcf_yoy`, `net_debt_yoy`, `ebit_margin_delta`
- Health score [0–100] on four dimensions: profitability, cash quality, balance sheet, momentum

### What's hollow / missing

- **No numeric signal thresholds** — leverage ratio, runway quarters, margin expansion are not independently computed or configurable
- **No per-company risk profile** — all companies evaluated against same regex patterns and severity keywords
- **No configurable threshold system** — hardcoded keywords determine severity, not user-defined or sector-adjusted thresholds
- **No signal inventory table** — risk signals are narrative-only, not quantitative
- **`risk_signals.py` does not exist** — the offline SQLite-based signal pipeline referenced in planning docs was never built
- **`derived_metrics.py` does not exist** as a standalone script — metrics are computed inline at query time
- **`run_extraction_quality_cycle.sh` does not exist** — no automated extract→audit→derive→signal→coverage pipeline script

### Pipeline architecture: unified or split?

**UNIFIED.** There is one pipeline, not two:

1. Ingestion: document → multipass LLM extraction (Pass 3b) → `asx_risk_notes` (Postgres)
2. Query: `/api/analysis/risk` → `risk_module.py` aggregates notes + RAG + news → deterministic response

There is no offline SQLite-based signal computation. The "two pipeline" concern from planning docs is unfounded — only the live Postgres path exists.

### Signals inventory

| Signal | Implemented | Data Source | Storage | Quantitative |
|--------|-------------|-------------|---------|--------------|
| Risk summary (narrative) | YES | LLM Pass 3b | `asx_risk_notes.risk_summary` | No |
| Risk bullets (list) | YES | LLM Pass 3b | `asx_risk_notes.risk_bullets` | No |
| Guidance summary | YES | LLM Pass 3b | `asx_risk_notes.guidance_summary` | No |
| Material changes | YES | LLM Pass 3b | `asx_risk_notes.material_changes` | No |
| Confidence (extraction) | YES | LLM Pass 3b | `asx_risk_notes.confidence_narrative` | Yes (0–1) |
| Risk category (4 types) | YES | Regex classification | Computed at query time | No |
| Severity estimate | YES | Keyword matching | Computed at query time | No (ordinal) |
| Financial health score | YES | Derived metrics | Computed at query time | Yes (0–100) |
| Leverage ratio | NO | — | — | — |
| Cash runway (quarters) | NO | — | — | — |
| Margin expansion/contraction | NO | — | — | — |
| Piotroski F-Score | NO | — | — | — |
| Beneish M-Score | NO | — | — | — |
| Altman Z-Score | NO | — | — | — |

---

## 2. External Content & Transcript Pipeline

### What's built end-to-end

**Three working ingestion paths:**

1. **Resource Library** (`scripts/resource_library_workflow.py`) — PDF/TXT/MD → heuristic or LLM summary → interactive CLI review (approve/reject/edit) → `data/resource_library/approved/` → context pack assembly. **Siloed from main RAG pipeline** — approved content is stored as Markdown packs, not indexed in Qdrant.

2. **YouTube Transcripts** (automated) — `youtube_transcript_fetcher.py` polls channels via `yt-dlp` + `youtube-transcript-api` → drop file to `inbox/transcripts/` → `TranscriptWatcher` processes → chunks indexed to Qdrant `commentary_chunks` → registered in `source_registry.jsonl`. **Production-ready, no approval gate.**

3. **Manual Transcript Ingest** — `scripts/ingest_transcript.py <file> --speaker X --published-at ISO8601` → same Qdrant indexing path as automated.

**Supported source types (commentary_ingest.py):**

| Type | Weight | Half-life | Status |
|------|--------|-----------|--------|
| `book` | 1.0 | 3650 days (~10yr) | API exists, no CLI |
| `youtube_transcript` | 0.55 | 14 days | Fully functional |
| `podcast_transcript` | 0.55 | 14 days | Functional (manual ingest) |
| `market_commentary` | 0.45 | 7 days | Functional (manual ingest) |
| `news_article` | 0.5 | 1 day | Via news pipeline |

**Decay mechanism:**
```
final_score = relevance_score × source_weight × credibility_weight × recency_decay
recency_decay = 2^(-(days_since_published / half_life_days))
```

### What's hollow / missing

- **Resource Library is siloed** — approved content stored as Markdown files, not indexed in Qdrant. Not queryable via RAG.
- **No approval gate for transcripts** — auto-ingested to Qdrant; `review_status="pending"` field exists in source registry but is not enforced.
- **No book ingest CLI** — `ingest_book()` API exists in `source_registry.py` but no command-line entry point.
- **No non-ASX PDF structured extraction** — Resource Library does text extraction only (PyMuPDF), no table/financial parsing for external documents.

### YouTube/transcript support: EXISTS — production-ready

- `youtube_transcript_fetcher.py` — channel registry, `yt-dlp` video listing, `youtube-transcript-api` transcript fetch
- `transcript_watcher.py` — drop-file processing with YAML front-matter metadata
- `run_transcript_daemon.py` — polling daemon for `inbox/transcripts/`
- `ingest_transcript.py` — CLI for manual ingestion
- **Gap:** No direct "paste a YouTube URL and ingest" flow — requires channel registry or manual drop file.

### Approval/decay mechanism: PARTIAL

- **Decay:** FULLY IMPLEMENTED — exponential decay with configurable half-lives per source type
- **Approval:** EXISTS for Resource Library (interactive CLI), ABSENT for transcripts/commentary
- **Strategy influence gate:** NOT IMPLEMENTED — no mechanism to flag content as "influences investment thesis" vs "background context"

### Embedding backend consistency: CONFIRMED

- Backend: `nomic-embed-text` via Ollama/llama.cpp HTTP endpoint (configurable via `EMBEDDING_URL` or `LLAMACPP_URL`)
- Cockpit: delegates to backend via `rag_query()` — does not embed locally
- `sentence-transformers/bge-large-en-v1.5` reference in `qual_context_bootstrap.py` is a **dead default** — overridden at runtime by `nomic-embed-text`
- Commentary weighting caps commentary at 25% of top evidence relevance (`commentary_weight_max=0.25`)

---

## 3. Cockpit Memory & Session Persistence

### What's actually stored across sessions

**SQLite state DB tables (`cockpit/storage/state.py`):**

| Table | Purpose | Persistence |
|-------|---------|-------------|
| `chat_messages` | Per-thread chat history (last 200) | Per-thread |
| `jobs` | Action execution records | Durable |
| `analysis_exports` | Analysis output snapshots | Durable |
| `watchlist` | Tracked tickers (ticker + added_at) | Durable |
| `update_events` | Per-ticker update summaries | Durable |
| `entity_observations` | Per-ticker research observations (max 300 chars, max 8) | Durable |
| `user_preferences` | User settings (key-value) | Durable |
| `session_summaries` | Cross-session context (up to 3 recent) | Durable |

**Agent memory layers (3-tier):**

1. **Session memory** — optional OpenViking integration, searches prior turns, returns up to 3 relevant records. Best-effort, degrades to empty list.
2. **Markdown filesystem** — `MEMORY.md` (prefs), `research/<TICKER>.md` (findings), `sessions/current.md` (JSONL turns), `daily/<DATE>.md` (compacted summaries)
3. **Semantic search** — optional SQLite-vec backend for embedding-based retrieval of memory chunks

**Company dossier** (`~/.tenn/memory/dossiers/<TICKER>.jsonl`) — research findings with `ticker`, `finding`, `source`, `confidence`, `category`, `timestamp`

### Per-company analytical memory: PARTIAL

- **Entity observations** store up to 8 short observations per ticker (300 char limit)
- **Dossier service** stores research findings per ticker (JSONL, unbounded)
- **Context assembly starts fresh** — `gather_local_context()` fetches live data, does NOT inject prior session conclusions or analysis decisions
- **No mechanism to recall** "last time I analyzed BHP, I concluded X" — each analysis is independent

### Strategy/buy-criteria storage: ABSENT

- **No `UserStrategy` model** in Postgres
- **No `buy_criteria` table** in SQLite
- **No tool to define/store/recall** buy criteria, entry/exit rules, or investment thresholds
- **Alert thresholds are hardcoded** in `alerts.py`: `3%` 1D move, `-8%` 20D momentum, `40%` volatility, `-12%` drawdown, `48h` staleness — not user-configurable
- **No `/strategy` or `/criteria` slash commands** — only `/watch` family exists

### Watchlist: schema, fields, trigger mechanism status

**Schema (SQLite):**
```sql
watchlist (
    ticker TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
)
```

**Operations implemented:** `add`, `remove`, `list`, `clear`

**NOT implemented:**
- `/watch sync` — parsed in `conversation_commands.py` but no handler exists
- **Trigger conditions** — no per-ticker buy/sell condition storage
- **Narrative monitoring** — no mechanism to detect "criteria met" events
- **Metadata per ticker** — no notes, thresholds, decision rationale, or risk assessment attached

**Additional gap:** `derive_conversational_command()` in `conversation_commands.py` is defined but **never called** — natural language watchlist commands are parsed but not wired into the message handler.

---

## 4. Gap Analysis — Priority Order

| # | Gap | Impact | Scope |
|---|-----|--------|-------|
| 1 | **No quantitative risk signals** (leverage, runway, Z-score, F-score) | Cannot flag deteriorating companies numerically; risk module is narrative-only | Medium |
| 2 | **No user-defined buy criteria / strategy persistence** | Cockpit cannot remember or act on investment decisions across sessions | Medium |
| 3 | **No watchlist trigger mechanism** | Watchlist is a passive list; no "alert me when X meets condition Y" | Medium |
| 4 | **No per-company analytical memory injection** | Each analysis starts fresh; prior conclusions lost | Small–Medium |
| 5 | **Resource Library siloed from RAG** | Approved books/frameworks not queryable via main retrieval pipeline | Small |
| 6 | **No transcript approval gate** | Transcripts influence RAG ranking without user confirmation | Small |
| 7 | **Alert thresholds hardcoded** | Users cannot customize sensitivity per ticker or globally | Small |
| 8 | **Conversational commands not wired** | `/watch` natural language parsing exists but is dead code | Small |
| 9 | **No Appendix 5B Section 8 extraction** | Cash runway (quarters of funding) not extracted from 5B reports | Medium |
| 10 | **No insider transaction signal** (Appendix 3Y) | Director buying/selling not tracked or surfaced | Medium |

---

## 5. Candidate Next Modules

### Piotroski F-Score (9-point)
- **Data needed:** Revenue, gross profit, ROA, operating CF, long-term debt, current ratio, shares outstanding, gross margin, asset turnover — all YoY
- **Available in Postgres:** Revenue, EBIT (proxy for operating income), operating CF, net debt, total assets — YES. Gross profit, current ratio, shares outstanding — NOT EXTRACTED. Gross margin derivable if gross profit exists.
- **Complexity:** Medium — 6 of 9 variables available; remaining 3 (gross profit, current ratio, shares outstanding) need extraction additions
- **Feasibility:** HIGH for a partial (6/9) F-Score; MEDIUM for full 9-point

### Beneish M-Score (8-variable + 5-variable ASX fallback)
- **Data needed:** Days sales receivable, gross margin, asset quality, sales growth, depreciation, SGA expense, leverage, total accruals
- **Available in Postgres:** Revenue (for sales growth), depreciation — partial. Receivables, SGA, total accruals — NOT EXTRACTED.
- **Complexity:** Large — requires extracting 5+ additional line items from financial statements
- **Feasibility:** LOW without significant extraction broadening

### Altman Z″-Score (non-manufacturing variant)
- **Data needed:** Working capital, retained earnings, EBIT, book value of equity, total assets, total liabilities
- **Available in Postgres:** EBIT, total assets (partial), net debt — partial. Working capital, retained earnings, book equity — NOT EXTRACTED.
- **Complexity:** Medium — 3 additional line items needed
- **Feasibility:** MEDIUM — achievable with targeted extraction additions

### Appendix 5B Cash Runway (Section 8)
- **Data needed:** Section 8.1 "estimated quarters of funding available" — a single integer field
- **Available in Postgres:** NOT EXTRACTED — this is a specific line item in Appendix 5B reports
- **Complexity:** Small — add one field to Pass 3a or create Pass 3c for 5B-specific extraction
- **Feasibility:** HIGH — single field, well-defined location in document, high impact for pre-revenue companies

### Director Transaction Signal (Appendix 3Y)
- **Data needed:** Director name, transaction type (buy/sell/exercise), shares, price, date
- **Available in Postgres:** NOT EXTRACTED — Appendix 3Y is a separate document class
- **Complexity:** Medium — requires new document class handler and structured extraction
- **Feasibility:** MEDIUM — well-structured document format but new extraction pipeline needed

### Sentiment Pipeline (FinBERT fast + LLM deep)
- **Data needed:** Text from risk notes, news, announcements
- **Available:** YES — risk_summary, risk_bullets, news_chunks all exist in Qdrant/Postgres
- **Complexity:** Medium — FinBERT inference (can run on existing GPU), LLM deep path via existing llama.cpp
- **Feasibility:** HIGH — data exists, infrastructure exists, just needs scoring layer

### YouTube/Transcript Ingest with Decay and User Confirmation
- **Status:** Ingest + decay BUILT. Missing: approval gate before Qdrant indexing, direct URL→transcript flow
- **Complexity:** Small — add review_status enforcement in commentary_ingest.py, add URL ingest command
- **Feasibility:** HIGH

### Strategy Workshopping Schema
- **Data needed:** New schema: per-ticker buy criteria, risk thresholds, decision rationale, user-confirmed
- **Available:** Nothing — entirely new capability
- **Complexity:** Medium — new SQLite tables, new tools, context injection changes
- **Feasibility:** HIGH — well-scoped, no external dependencies

### Watchlist Narrative Monitoring
- **Data needed:** Strategy schema (above) + event detection loop + notification mechanism
- **Depends on:** Strategy workshopping schema must exist first
- **Complexity:** Medium — periodic scan against stored criteria, alert generation
- **Feasibility:** MEDIUM — requires strategy schema + event loop + alerting

### Per-Company Analytical Memory
- **Data needed:** Structured storage of prior analysis conclusions, injected into context assembly
- **Available:** Dossier service exists (JSONL) but not injected into `gather_local_context()`
- **Complexity:** Small — wire dossier findings into context assembly, add "conclusion" observation type
- **Feasibility:** HIGH — infrastructure mostly exists, needs wiring

---

## 6. Architecture Concerns

### No invariant violations found
The risk module correctly uses the canonical extraction pipeline (Pass 3b) and does not bypass the single-source-of-truth rule. All risk data flows through Postgres.

### Embedding backend consistent
All pipelines use `nomic-embed-text` via Ollama/llama.cpp. The `bge-large-en-v1.5` reference in Cockpit bootstrap is a dead default, not live. **CONFIRMED consistent.**

### Resource Library is architecturally siloed
Approved resources are stored as Markdown files on disk, not indexed in any vector store. This means high-quality approved content (books, frameworks) is invisible to RAG queries. This is a design gap, not a bug — the Resource Library predates the Qdrant-based retrieval pipeline.

### Conversational commands are dead code
`conversation_commands.py` defines natural language → slash command mappings but `derive_conversational_command()` is never called. This is harmless dead code but creates a false impression of capability.

### Commentary weight cap may be too aggressive
`commentary_weight_max=0.25` in `research_context_builder.py` caps all external content (transcripts, podcasts, commentary) at 25% of top evidence relevance. For companies with thin ASX filing coverage, this may suppress useful external context. Worth monitoring.

### No duplicate pipeline concern
The "two risk pipelines" hypothesis is disproven — only the live Postgres path exists. No SQLite-based offline signal computation was ever built.

---

## 7. Recommended Phase 2 Scope

### Phase 2A — Quick Wins (Small scope, high impact)

1. **Appendix 5B Cash Runway Extraction** — Add Section 8.1 "quarters of funding" to Pass 3a/3c. Single field, high impact for pre-revenue company screening. ~50 lines.

2. **Per-Company Analytical Memory** — Wire dossier findings into `gather_local_context()`. Add "conclusion" and "thesis" observation types. When analyzing a company, inject prior conclusions. ~100 lines.

3. **Wire Conversational Commands** — Call `derive_conversational_command()` in the chat message handler. Activate natural language watchlist commands. ~20 lines.

4. **Transcript Approval Gate** — Enforce `review_status` check in `commentary_ingest.py` before Qdrant indexing. Add `/review` command for pending transcripts. ~80 lines.

### Phase 2B — Core Intelligence (Medium scope)

5. **Quantitative Risk Signals** — Implement leverage ratio, margin trend, and cash runway as computed signals with configurable thresholds. Store in new `risk_signals` table or extend `financial_metrics.py`. Feed into `/api/analysis/risk` response.

6. **Piotroski F-Score (partial)** — Implement 6/9 score from available Postgres data. Surface in analysis endpoint and Cockpit context.

7. **Strategy Workshopping Schema** — New SQLite tables for per-ticker buy criteria, risk thresholds, decision rationale. New tools: `define_buy_criteria`, `recall_investment_decision`. Inject into context assembly.

8. **Sentiment Scoring Layer** — FinBERT fast path on existing risk notes and news. Store sentiment score per document. Surface in risk analysis.

### Phase 2C — Full Intelligence Loop (Large scope)

9. **Watchlist Narrative Monitoring** — Periodic scan of watchlist tickers against stored criteria. Generate alerts when conditions met. Requires Phase 2B items 5+7.

10. **Director Transaction Signal** — New Appendix 3Y document class handler. Structured extraction of insider transactions. Integrate into risk module.

11. **Resource Library → RAG Integration** — Index approved Resource Library content into Qdrant as a `reference` corpus type with book-level decay (3650 days).

12. **User-Configurable Alert Thresholds** — Replace hardcoded constants in `alerts.py` with per-user or per-ticker configurable values stored in state DB.

### Ordering rationale
- 2A items are wiring/small additions that unlock immediate value
- 2B items build the quantitative intelligence layer that is entirely absent today
- 2C items require 2B foundations and represent the full vision (narrative monitoring, strategy persistence, decision memory)
