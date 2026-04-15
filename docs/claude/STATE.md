# STATE.md — Active Work Tracker

> **Purpose:** Single source of truth for what is planned, in-flight, verified, and shipped.
> Update this file at the end of every session alongside the milestone commit.
> For detailed context on any item, follow the linked doc or run `git log --oneline`.

Last updated: 2026-04-15 (cockpit issue capture: every web Cockpit tab now exposes a shared header control that captures a screenshot of the current cockpit pane, collects frontend/runtime context, and saves the report into `reports/cockpit/flagged_sessions/...` with `ui_issue_*` IDs and on-disk screenshot artifacts readable by Claude/Codex); 2026-04-14 (extraction truth prototype: backend real-gold eval now mints backend-owned review sessions for flagged documents, the verification UI can open those sessions directly from the real-gold table, and the saved review path still reuses backend provenance/snippet/wrong-queue state); 2026-04-13 (extraction cache hygiene + live-eval observability: Docling caches now record source PDF page count, reject obviously partial coverage before reuse, and delete stale cache artifacts before re-extraction; live eval now emits per-fixture progress lines and incremental JSON status; clean-cache bounded rerun restored QBE to 100% and BHP to 100% in the lane sweep, with MIN/TLS shares_outstanding still open); 2026-04-11 (cockpit web active-model switch-state fix: chat fallback status now uses backend-backed runtime model snapshots + normalized alias comparison; `docs/architecture/21_cockpit_client_contract.md` updated to require backend-authoritative active-model UX, plus prior Cockpit client contract addendum / observability / architecture index alignment); 2026-04-10 (session — local article print path via mounted reports corpus, article-request raw-JSON guard + refusal/print path, confirmation follow-up interpretation fix, web chat session-thread persistence fix, linked-ticker news retrieval fix, deterministic ticker-news fast path, cockpit launcher process-control audit, root-owned backend kill fallback hardening, cockpit web action execution endpoint + confirm payload normalization, adaptive GPU polling during active chat, chat stream cancel/status UX hardening, context endpoint transaction rollback fix, llama router service rename/switchover, local disk cleanup, docs alignment, safe final-answer streaming split, backend query orchestrator scaffold, company-memory qualitative store, market-memory shared context store, memo-to-memory signal routing, cockpit doc-grounding/local-context routing gate fix, chat GPU priority hardening, real-extraction eval local llama auth persistence fix, verification UI real-gold eval wiring + latest-run extraction review, backend-authoritative historical extraction-run review loading, shared-router extraction mutex + stale alias load fix, gold-eval route main-thread fix, cockpit good-feedback capture, ticker-ingest routing fix, daily announcement date alias normalization)
Branch: plan/ideation-combinations-2026-04-11

## Legend

| Status | Meaning |
|--------|---------|
| `[ planned ]` | Scoped, not started |
| `[ in-progress ]` | Active — has open items or uncommitted work |
| `[ verified ]` | Confirmed working, tests passing, milestone committed |
| `[ shipped ]` | Merged to main or stable on a long-running branch |

---

## Active Workstreams

| Workstream | Status | Open items |
|------------|--------|------------|
| **bug-ui** | `[ verified ]` | None — claude agent deploy + on-demand debate UI complete (58ff4e85) |
| **extraction-hardening** | `[ in-progress ]` | (1) FX conversion logic not yet built. (2) AZJ font encoding confirmed unsolvable — threshold 0.0. (3) pymupdf quality gate added (flags `pymupdf_degraded`). (4) Live eval run 2026-03-27: 77.89% overall, 88.64% excl. AZJ. (5) Synthetic fixture hardening scaffold now implemented (pure doc-level scoring, context quarantine, optional metric abstain handling). |
| **news-pipeline** | `[ verified ]` | Embedding routing fixed, asx_docs rebuilt at 768-dim (a4564e47). **Default provider switched to newspaper4k** (2026-03-27): 54 AU finance sources (AFR, Stockhead, MarketIndex, SMH, ABC, etc.) with Scrapling/Playwright fallback. EODHD and GDELT suspended from main pipeline — poor ASX coverage. |
| **eval-fixtures** | `[ verified ]` | 13 fixture JSONs now in repo. Last fully live-validated set remains 9 fixtures on 2026-03-27. AZJ threshold=0.0, FMG threshold=0.60, RMS threshold=0.70. 88.64% excl. AZJ on the validated set. |
| **extraction-quality** | `[ in-progress ]` | 88.64% accuracy on 8 fixtures (excl. AZJ). Docling restored as default (877a8203). ANZ ~90.9% after banking-sector fixes (e1710290, 8e4ec1b3). **Prose fallback for shares_outstanding** (88e47336): regex extraction from note sections — covers ANZ Note 13 pattern + 3 other ASX conventions. Real-eval runner now persists local `LLM_API_KEY` by mirroring env, detecting `llama-server --api-key`, or falling back to `local-openai-key`; focused script test coverage added. Verification UI manual review now re-runs selected PDFs before loading a session, can invoke a backend real-gold eval over `data/extraction_gold_real` using the current multipass extraction path, and can load backend-authoritative prior extraction runs by explicit `run_id` so runs launched outside Cockpit remain reviewable. Gold-set HTTP execution now uses an async FastAPI route wrapper so the real extraction pipeline stays on the main thread instead of AnyIO’s sync worker thread; a temporary backend on `:8010` validated `POST /api/extraction-eval/real-gold` with `limit=2` returning `200` over real HTTP. **2026-04-14:** flagged real-gold results now create backend-owned review sessions with saved provenance/snippet evidence and a direct UI handoff from the gold-eval table back into the existing manual review session flow. **2026-04-13:** Docling cache hygiene now rejects partial page-coverage caches and the live eval writes per-fixture progress. Clean-cache bounded rerun over BHP/MIN/QBE/TLS restored BHP and QBE to 100% in-lane; remaining confirmed residuals are MIN `shares_outstanding` and TLS `shares_outstanding` only. |
| **extraction-perf** | `[ verified ]` | Docling default restored (877a8203). PyMuPDF available via EXTRACTION_BACKEND=pymupdf. |
| **cockpit-agent** | `[ verified ]` | Agent mode + ToolExecutor verified via Textual Pilot 2026-03-27: all 7 checks PASS, 217 unit tests. |
| **cockpit-strategy** | `[ verified ]` | Strategy schema (d173a8da): global + ticker criteria tables, StrategyService, /strategy commands, natural language rules, context injection. 10 tests. |
| **cockpit-sourcing** | `[ verified ]` | Evidence sourcing (2e9c3ddb): SourcesFormatter, sources metadata in gather_local_context, /sources on\|off toggle. 6 tests. |
| **cockpit-routing** | `[ in-progress ]` | Chat routing visibility + extraction guard (f037aa09): per-response footer [backend\|model\|latency\|cost], extraction pre-flight guard with auto-model-load via router API, `.env` loading fixed in cockpit entrypoint. Ticker fast-path false positives fixed (2cfb991e): stopwords expanded, _FOLLOW_UP_RE narrowed to topic-referential only. New local patch narrows the orchestrator early-return gate so ticker queries can fall back to the existing local-context path when document grounding is required or orchestrator evidence is empty. Follow-up patch prevents generic ticker overviews from attaching weak linked-ticker news context and adds a no-financials prompt guard so the direct-answer path does not invent metric tables when canonical financial truth is absent. Cockpit chat now also yields GPU priority to any competing llama runtime or non-chat compute process and routes to the API client instead of contending for VRAM. Current local patch hardens the shared-router extraction mutex across pipeline and real-gold eval entrypoints, blocks local chat during extraction when no API backend is configured, resolves stale llama.cpp model aliases before `/models/load`, resolves Anthropic API availability from effective Cockpit config, treats preferred-model preload as extraction-aware best effort instead of a warning-worthy startup failure, prevents blank `.env.local` secrets from erasing working `.env` API keys at backend launch, routes bare `ingest <ticker>` prompts to the single-ticker backfill action, normalizes `date=today` to `YYYY-MM-DD` before daily announcement execution, and aligns the web chat pre-stream "switching model" status with backend-backed runtime snapshots so stale `local` placeholders or alias/display-name differences do not trigger false switch waits. Focused routing/news tests previously passed; live extraction mutex now routes to Claude successfully when the effective key is non-empty. |
| **gpu-process-rails** | `[ verified ]` | Canonical port manifest (§9.4), agent spawn protocol (§9.5), `gpu_process_guard.sh`, `llamacpp_manager.py` topology check. L022 logged. |
| **llamacpp-runtime** | `[ verified ]` | Tesla M40 load path fixed for `model:gpt-oss-20b`: forced KV-cache quantization removed from launcher defaults; router now loads on GPU and serves completions. |
| **analysis-modules** | `[ verified ]` | 7 modules (+ sentiment), orchestrator, context_loader (Yahoo price fallback), watchlist scanner (7 alert rules), API endpoints, scale validation gate, extraction expansion (total_equity, interest_expense). 48+22 tests. D2 live-tested. Real-data validated (RIO, BHP). **Sentiment RAG wiring:** modules declare RAG queries via `rag_queries` property; orchestrator merges into ContextRequest; `analysis_rag_adapter` bridges Qdrant; sentiment scores news_chunks + commentary_chunks. Architecture doc 1151 lines. |
| **model-eval** | `[ verified ]` | Qwen 3 14B evaluated (85.26%) vs Qwen 2.5 14B (89.47%) — current model stays. |
| **docs-governance** | `[ in-progress ]` | Root startup docs aligned to the canonical backend entrypoint. Repository-audit instructions updated to use actual repo manifests. Backend API surface, extraction, embeddings, routing, scripts index, portfolio module docs, Cockpit control-plane docs, and eval-fixture architecture docs refreshed. Startup docs now reflect `cockpit restart backend` full-functionality defaults. Cockpit feedback docs now point operators to `/api/cockpit/feedback/flags*` as the canonical read path, note that save persistence is immediate, and document both `poor` and `good` feedback capture for later review/training. **Cockpit contract addendum shipped:** `docs/architecture/21_cockpit_client_contract.md` (pointer from `SYSTEM_CONTRACT.md` §1.2), conformance matrix, and `docs/ops/cockpit_operator_observability.md` runbook — latest addendum update now also documents that active-model and model-switch UX in the web client must be backend-authoritative rather than driven by stale client placeholders. Remaining governance is keeping the matrix current when `cockpit_api` / BFF routes change. |
| **storage-migration** | `[ verified ]` | Tenn runtime data migrated to `/mnt/nvme/tenn/runtime-data`; GGUF router assets migrated to `/mnt/nvme/tenn/models`; root Ollama store pruned to `qwen2.5:32b` + `gpt-oss:20b-cloud`; inactive Ollama models archived to `.archives/ollama-root-store-2026-04-07`; docs/configs aligned. Validation: docs-heavy workload showed low short-term IO PSI and ~1% `wa` after warm-up. **2026-04-09:** Old 500GB Barracuda (sda) wiped and reformatted as single ext4 `hdd-cold` (466G) at `/mnt/hdd-cold`; old PC backup data (135,412 files) verified and archived to external USB drive; redundant 41G `old_pc_backup_2012` deleted from sdb2 (152G free now); all drives labeled (`nvme-system`, `hdd-data`, `ssd-cache`, `hdd-cold`); llmfit updated 0.8.4→0.9.2; llama-server/llama-cli symlinked to `~/.local/bin`. |
| **memory-orchestration** | `[ verified ]` | Safe final-answer streaming is live. Backend `query_orchestrator.py` now classifies and source-plans live chat queries across `financial_truth`, `company_memory`, and `market_memory`, with `financial_truth` enforced first for numeric queries. `company_memory.py` and `market_memory.py` provide separate qualitative-only SQLite stores with dedupe/reinforce/supersede/contradict/expire rules and explicit blocks on financial-metric signal types. `memory_signal_router.py` converts commentary/news memos into qualitative company/sector/macro signals, and `extract_and_store(...)` now routes those signals into memory automatically. Remaining follow-up is broader product-level coverage, not missing architecture wiring. |

---

## Pipeline Build Status

From [docs/architecture/14_roadmap_and_modules.md](../architecture/14_roadmap_and_modules.md).

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| 1. Data acquisition | Filings, news, prices, fundamentals | `[ in-progress ]` | Filings + news operational; prices and fundamentals coverage incomplete |
| 2. Retrieval (RAG) | `POST /rag/query` — semantic search over ingested docs | `[ verified ]` | Operational; news_chunks resynced with relevance-ordered tickers |
| 3. Analysis modules | Risk, valuation, moat, catalysts, ROIC, balance sheet, sentiment | `[ verified ]` | 7 modules, D2 live-tested, 48 tests, API endpoints, cockpit "analyse" command, watchlist scanner. Architecture doc 1151 lines. |
| 4. Portfolio module | Exposure, correlation, position sizing | `[ verified ]` | 6 sub-modules built (4c991798): valuation_summary, moat_quality, catalyst_calendar, risk_aggregation, position_sizing, weights. PortfolioAnalyser orchestrator. |
| 5. Outputs | Artifacts written under `reports/` | `[ in-progress ]` | Analysis artifacts writing to reports/analysis/{ticker}/. Portfolio artifacts to reports/portfolio/. Ticker backfill in progress (14 docs registered, extraction running). |

---

## Infrastructure Stages

From [docs/claude/introduction-plan.md](introduction-plan.md).

| Stage | Item | Status |
|-------|------|--------|
| 1 | Documentation normalization (CLAUDE.md, docs/claude/) | `[ shipped ]` |
| 2a | Failure model summary | `[ shipped ]` |
| 2b | Vector baseline threshold docs | `[ shipped ]` |
| 2c | OpenClaw/llama.cpp ops skill | `[ deferred ]` — re-evaluate if OpenClaw re-enters active use |
| 2d | Domain skill: news substrate | `[ shipped ]` |
| 2e | Domain skill: model routing | `[ shipped ]` |
| 2f | `commentary_chunks_v2` fallback policy | `[ shipped ]` |
| 3a | Markdown hygiene pre-push hook | `[ shipped ]` |
| 3b | Ruff + pytest enforcement hooks | `[ shipped ]` |
| 3c | Claude Code session hooks | `[ shipped ]` |
| 3d | CI workflow (GitHub Actions) | `[ shipped ]` — `.github/workflows/ci.yml` (ruff + pytest, `live_eval` excluded); see `docs/validation_baseline.md` |

---

## Recently Shipped Milestones

| Commit | Workstream | Summary |
|--------|------------|---------|
| (this session) | cockpit-ui / cockpit-feedback | Every Cockpit web tab now has a shared `Capture issue` control in the header; it records a screenshot of the current pane plus frontend/runtime context and saves a `ui_issue_*` report under `reports/cockpit/flagged_sessions/...` with `ui-screenshot.png` for Claude/Codex review. |
| (this session) | extraction-truth | Real-gold eval now emits backend-owned `review_session_id` handoffs for flagged documents, Cockpit can open those saved sessions directly from the gold-eval table, and the prototype continues to use the existing extraction-review provenance/snippet/wrong-queue path. |
| (this session) | extraction-quality | Docling cache hygiene: reject partial/stale cache coverage, persist source PDF page counts, and delete stale cache files before re-extraction. Live eval now emits per-fixture progress lines plus incremental JSON status. Clean-cache bounded rerun: BHP 100%, QBE 100%, MIN shares_outstanding still null, TLS shares_outstanding still null. |
| (this session) | storage-housekeeping | Old 500GB Barracuda wiped/reformatted as ext4 `hdd-cold` (466G) at `/mnt/hdd-cold`; old PC backups verified (135,412 files) and archived to external USB; redundant 41G backup deleted from sdb2; all drives labeled; llmfit 0.8.4→0.9.2; llama-server symlinked to PATH. ASX filing PDFs (149G) moved NVMe→hdd-cold with symlink; stale SSD Ollama models deleted; Docker pruned; llmfit cache redirected to hdd-cold. NVMe 52G→193G free. |
| (prev session) | runtime-cleanup | Removed the stale `/tmp/llama-server-8001.log` orphan log, cleaned npm/OpenCode/Cursor disposable caches, and improved root-disk headroom to roughly `53G` free while keeping the managed router healthy on `:8001`. |
| (this session) | llamacpp-runtime | Renamed the checked-in chat/router user unit to `llama-cpp-router.service`, aligned installer/docs/runtime discovery, and switched the live `:8001` router from an orphaned legacy process to the managed router service. |
| (this session) | cockpit-ui / cockpit-api | Confirmed action proposals from web chat now execute via `POST /api/cockpit/action/execute`; frontend normalizes `action_preview` payload shapes (`action_id`/`arguments` vs `id`/`args`) to prevent `Action "undefined"` failures. |
| (this session) | cockpit-routing / cockpit-actions | Bare `ingest <ticker>` prompts in web chat now propose `single_ticker_announcement_backfill` instead of market-wide daily ingest, and `daily_announcement_ingest` now normalizes `date=today` to a concrete `YYYY-MM-DD` before execution. |
| (this session) | cockpit-feedback | Flagged chat saves now persist `bundle.json`/`summary.md` immediately and return `report_id` without waiting on llama.cpp review; optional flagged-chat analysis now runs in a background thread and can populate `analysis.json` shortly after save. |
| (this session) | cockpit-model-discovery | `/api/cockpit/models` now works in Docker-backed backend runs: the backend container mounts host GGUF directories read-only at `/models/{nvme,ssd,hdd}`, model discovery falls back to llama-server registry data when direct scans are unavailable, and `/api/cockpit/config` reports the currently loaded llama-server model instead of a stale config default. |
| (this session) | cockpit-ui | Sidebar/system health polling is now adaptive: 3s while a chat completion is active and 15s when idle, improving GPU visibility during active model inference. |
| (this session) | cockpit-routing | HybridRouter now treats chat as the lowest-priority GPU consumer: if another llama runtime or unrelated compute process is present on the GPU, cockpit chat routes to the API client instead of competing locally. |
| (this session) | backend-context | `/api/context/ticker` query error handling now rolls back failed DB transactions and treats missing `cockpit_announcement_context` table as non-fatal instead of poisoning subsequent reads. |
| (this session) | cockpit-ui | Sidebar GPU indicator now includes temperature, and web chat streams explicit execution-stage status events (`Resolving request context`, tool execution, synthesis, final rendering) instead of a generic `Analyzing market data...` placeholder. |
| (this session) | cockpit-ui | Sidebar now shows a host-level GPU indicator sourced from the Next.js `/api/cockpit/health` wrapper, with live `nvidia-smi` name/utilization/VRAM data instead of the backend container’s blind spot. |
| (this session) | cockpit-launcher | `cockpit kill root` now falls back from `lsof` to `ss` for listener discovery and re-checks ports after wrapper kills, so orphaned `next-server` listeners on `:8081` are actually removed. |
| (this session) | cockpit-launcher | `cockpit kill root` now cleans stale Next.js UI processes and both configured UI ports, and `cockpit start web/new` preflight the target port before launch so stale listeners fail fast instead of surfacing as misleading `EADDRINUSE`. |
| (this session) | cockpit-launcher | Process-control commands now share a single sudo-fallback kill path, so `cockpit kill backend`, `cockpit restart backend`, llama shutdown, and bugagent cleanup can remove root-owned processes instead of leaving stale runtimes behind. |
| (this session) | news-retrieval / cockpit | `bhp news` now matches linked tickers in `news_chunks`, dedupes duplicate article chunks, compacts `search_news` payloads for model use, and short-circuits bare ticker-news commands to a direct headline list instead of the agent loop. |
| (this session) | cockpit-web-chat | Web chat now persists user/assistant turns under the provided `session_id` instead of a shared `global-main` thread, so short follow-ups like `ok` keep the immediately prior context instead of resetting to a generic reply. |
| (this session) | cockpit-followups | Short acknowledgements (`ok`/`okay`/`yes`/`sure`) are now interpreted as confirmations of the last assistant offer or yes/no question, with a direct summary-offer path for `I can summarize it` style follow-ups. |
| (this session) | cockpit-followups / agent-loop | Article reproduction requests now short-circuit to a clean refusal, and the agent loop treats bare `fetch_url` argument blobs (`{"url":...,"max_chars":...}`) as malformed tool output to recover from rather than showing raw JSON to the user. |
| (this session) | cockpit / local news corpus | Cockpit can now print the full locally stored article body for a recently referenced news URL by reading `articles.body` from `news_articles.sqlite`; the backend compose service now mounts the workspace `../reports` directory so the live container can see the local corpus. |
| (this session) | cockpit-ui / cockpit-api | SSE chat now emits canonical final text in the `done` event and the Next UI prefers that value over buffered chunks, preventing raw tool-call JSON from being committed as the assistant reply. |
| (this session) | memory-orchestration | Split Cockpit agent streaming into non-streaming structured planning plus plain-text final synthesis with timeout fallback; added backend query orchestrator scaffold and a separate qualitative-only company-memory SQLite store with explicit update rules. |
| (this session) | memory-orchestration | Added `market_memory.py`: separate SQLite-backed sector and macro context store with qualitative-only guardrails, explicit update rules, and ticker-to-sector retrieval for shared market context. |
| (this session) | memory-orchestration | Added `memory_signal_router.py` plus extractor `extract_store_and_route(...)` hooks so commentary/news memos can be converted into qualitative company, sector, and macro signals and persisted into the new memory stores. |
| (this session) | memory-orchestration | Wired live Cockpit/backend chat through `query_orchestrator.py`, using backend financial-truth context plus company/market memory for retrieval-driven answers while preserving final-synthesis-only streaming; `extract_and_store(...)` now auto-routes memo signals into memory in production flow. |
| (this session) | cockpit-launcher | `cockpit restart backend` now rewrites `.env.docker`, enforces `nomic-embed-text`, frees conflicting Ollama runners before backend startup, routes embeddings through Ollama correctly, and leaves detached llama.cpp chat alive after the command exits. |
| (this session) | agent-orchestrator | Replaced blocking native-CLI chat with Codex-backed run/SSE streaming, optimistic chat UI state, and explicit delegated-task events; verified with `npm test`, `npm run build`, `npm run smoke`, and live `/api/chat` SSE curl. |
| 52508567 | llamacpp-runtime | Stop forcing KV-cache quantization in llama.cpp launchers/runtime manager; `model:gpt-oss-20b` now loads on Tesla M40 and serves chat completions with GPU memory allocated. |
| 6e33d5d8 | cockpit-ui | Start the `sse.js` chat stream explicitly so the chat screen no longer gets stuck in `Analyzing market data...` without sending a request. |
| 88e47336 | extraction-quality | Prose fallback for shares_outstanding: regex extraction from note sections (ANZ Note 13 + 3 other patterns), sanity range gate, table priority preserved. 12 tests. |
| 42eadf64 | analysis-modules | Sentiment RAG wiring: modules declare RAG queries, orchestrator merges them, analysis_rag_adapter bridges Qdrant, sentiment scores news_chunks + commentary_chunks. 22 new tests. |
| f4e2f820 | cockpit | Align preboot routing docs and tests: cockpit LLM config authority, env-override gating, current preboot export behavior. |
| 0e651e8d | analysis-modules | Phase 3 complete: 6 analysis modules (balance_sheet, roic, valuation, risk, catalysts, moat), AnalysisModule Protocol, TickerContext, orchestrator, context_loader. 48 tests, 2350 lines. Qwen 3 14B evaluated and rejected (85.26% vs 89.47%). |
| adfec5ca | analysis-artifact-v0 | Deterministic `financial_snapshot_v0.json` from `asx_periodic_financials` → `reports/analysis/{TICKER}/`; `periodic_snapshot_export` + `export_financial_snapshot.py`. |
| 135440e1 | ops-commentary | Staging→Qdrant runbook (`docs/ops/commentary_staging_to_qdrant.md`), CLI `promote_staged_commentary.py`, CI `autodev/tests`, Pass3a bank-revenue prompt regression test. |
| 3a168c71 | ci | GitHub Actions: ruff + pytest with root `pytest.ini` (`live_eval` deselected); Qdrant/transcript tests aligned to commentary staging gate; `commentary_ingest` unused imports removed. |
| (this session) | cockpit-watchlist | Watchlist trigger mechanism: WatchlistTrigger orchestrator, `/watch scan` command, `scan_watchlist` agent tool, natural language routing. 10 tests. |
| 2cfb991e | cockpit-routing | Ticker fast-path false positives fixed: TICKER_STOPWORDS expanded (+21 words), _FOLLOW_UP_RE narrowed to topic-referential only, 9 regression tests. L029. |
| (prev session) | cockpit-routing | Chat routing visibility: per-response `[Claude API | model | latency | cost]` footer; extraction pre-flight guard with auto-model-load; `.env` loading in cockpit entrypoint (L027+L028). Renamed `model.gguf` → `mistral-7b-instruct-v0.2-q4_k_m.gguf`. |
| (this session) | cockpit-llm-client | Thread-local httpx + timeouts/limits for LlamaCpp/Ollama clients; `gpu_process_guard.sh` VRAM parse hardening; L026 in lessons.md. Reduces CLOSE_WAIT risk when health runs via `to_thread` during chat. |
| 2e9c3ddb | cockpit-sourcing | Evidence sourcing: SourcesFormatter footer (RAG hits, financial periods, dossier/strategy counts), /sources on\|off, show_sources preference. 6 tests. |
| d173a8da | cockpit-strategy | Strategy workshopping schema: global_strategy + ticker_strategy tables, StrategyService, /strategy list\|add\|decide\|delete, natural language routing, context injection above dossier. 10 tests. |
| (prev session) | gpu-process-rails | GPU process management: `gpu_process_guard.sh`, `llamacpp_manager.py` topology check, SYSTEM_CONTRACT §9.4+§9.5, CLAUDE.md pre-flight GPU field, L022+L023. Eval 89.47% PASS. |
| (prev session) | cockpit-agent | Agent system scaffold: HybridRouter, MemoryStore (SQLite-vec), SubAgentSpawner, ExtractionController, ModelRouter, system prompt, preboot per-function routing UI, chat.py integration. 53 tests. |
| (this session) | cockpit/llm | Router mode for llama-server: zero-downtime model switching via API, preset INI for per-model config, 12-model dropdown (filesystem + Ollama + HF cached), crash detection on model switch |
| (prev session) | eval-fixtures | Broadened to 9 fixtures: +ANZ (bank, AUD), +AZJ (transport, AUD), +CSL (healthcare, USD). MIN fixture completed to all 10 metrics. Claude API verification script built. 263 tests passing. |
| 483ce6d2 | extraction-quality | 98.3% accuracy — all eval gates green. 16 key fixes from 45% baseline. |
| 1429dcaa | cockpit | Fix llama.cpp port 8080→8001 in all cockpit defaults; align docs/scripts to canonical port 8001 (L015) |
| (prev session) | extraction-quality | Evidence-based quality assessment: 25 fixture values confirmed, live eval gap documented, MIN Pass 2 misclassification found |
| a4564e47 | news-pipeline | Fix embedding routing + rebuild asx_docs 768-dim |
| 58ff4e85 | bug-ui | Claude agent deploy + on-demand debate UI complete |
| b78b2964 | eval | Promote quarterly fixtures + add SEG non-mining fixture |
| 8db6a212 | extraction-hardening | FX policy doc, quarterly fixture, provenance script |
| 1d113788 | news-pipeline | Resync Qdrant news_chunks with relevance-ordered primary tickers |
| (this session) | storage-migration | Runtime data + GGUF models moved to NVMe, inactive root Ollama models archived to HDD, storage/docs/config surfaces aligned, docs-heavy validation no longer reproduced the earlier severe IO pressure. |
| (this session) | extraction-hardening | Added synthetic extraction-eval scaffold (`financial-engine_v2/backend/app/services/extraction_eval.py`), fixtures under `backend/tests/fixtures/extraction_eval/`, contract/taxonomy docs, and unit tests in `test_extraction_eval_harness.py` with deterministic scoring semantics. |
 
---

## Backlog (scoped but not started)

- ~~**Watchlist trigger mechanism**~~ — SHIPPED: `/watch scan`, `scan_watchlist` tool, `WatchlistTrigger` orchestrator
- ~~**Sentiment scoring layer**~~ — SHIPPED: modules declare RAG queries, orchestrator merges them, sentiment scores news_chunks + commentary_chunks via analysis_rag_adapter. 22 tests.
- **Alert thresholds from strategy** — replace hardcoded thresholds in alerts.py with user-defined strategy criteria
- **FX conversion logic** — build actual currency conversion; policy defined in `docs/architecture/16_currency_and_fx_policy.md`; blocked on product decision about which conversion source to use
- **Scrapling integration** — status unknown; see `docs/ops/scrapling_integration_note.md`
- **Recovery/reconstruction integration** — status unknown; see `docs/ops/recovery_reconstruction_integration_manifest.md`
