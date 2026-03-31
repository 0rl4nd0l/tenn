# STATE.md — Active Work Tracker

> **Purpose:** Single source of truth for what is planned, in-flight, verified, and shipped.
> Update this file at the end of every session alongside the milestone commit.
> For detailed context on any item, follow the linked doc or run `git log --oneline`.

Last updated: 2026-03-30 (session — cockpit docs alignment, startup docs correction, architecture/eval doc refresh)
Branch: cloud/session-20260319

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
| **extraction-hardening** | `[ in-progress ]` | (1) FX conversion logic not yet built. (2) AZJ font encoding confirmed unsolvable — threshold 0.0. (3) pymupdf quality gate added (flags `pymupdf_degraded`). (4) Live eval run 2026-03-27: 77.89% overall, 88.64% excl. AZJ. L019 logged. |
| **news-pipeline** | `[ verified ]` | Embedding routing fixed, asx_docs rebuilt at 768-dim (a4564e47). **Default provider switched to newspaper4k** (2026-03-27): 54 AU finance sources (AFR, Stockhead, MarketIndex, SMH, ABC, etc.) with Scrapling/Playwright fallback. EODHD and GDELT suspended from main pipeline — poor ASX coverage. |
| **eval-fixtures** | `[ verified ]` | 13 fixture JSONs now in repo. Last fully live-validated set remains 9 fixtures on 2026-03-27. AZJ threshold=0.0, FMG threshold=0.60, RMS threshold=0.70. 88.64% excl. AZJ on the validated set. |
| **extraction-quality** | `[ in-progress ]` | 88.64% accuracy on 8 fixtures (excl. AZJ). Docling restored as default (877a8203). ANZ 72.7% — banking revenue format regression to investigate. |
| **extraction-perf** | `[ verified ]` | Docling default restored (877a8203). PyMuPDF available via EXTRACTION_BACKEND=pymupdf. |
| **cockpit-agent** | `[ verified ]` | Agent mode + ToolExecutor verified via Textual Pilot 2026-03-27: all 7 checks PASS, 217 unit tests. |
| **cockpit-strategy** | `[ verified ]` | Strategy schema (d173a8da): global + ticker criteria tables, StrategyService, /strategy commands, natural language rules, context injection. 10 tests. |
| **cockpit-sourcing** | `[ verified ]` | Evidence sourcing (2e9c3ddb): SourcesFormatter, sources metadata in gather_local_context, /sources on\|off toggle. 6 tests. |
| **cockpit-routing** | `[ verified ]` | Chat routing visibility + extraction guard (f037aa09): per-response footer [backend\|model\|latency\|cost], extraction pre-flight guard with auto-model-load via router API, `.env` loading fixed in cockpit entrypoint. Ticker fast-path false positives fixed (2cfb991e): stopwords expanded, _FOLLOW_UP_RE narrowed to topic-referential only. L027+L028+L029. |
| **gpu-process-rails** | `[ verified ]` | Canonical port manifest (§9.4), agent spawn protocol (§9.5), `gpu_process_guard.sh`, `llamacpp_manager.py` topology check. L022 logged. |
| **analysis-modules** | `[ verified ]` | 7 modules (+ sentiment), orchestrator, context_loader (Yahoo price fallback), watchlist scanner (7 alert rules), API endpoints, scale validation gate, extraction expansion (total_equity, interest_expense). 48 tests. D2 live-tested. Real-data validated (RIO, BHP). Architecture doc 1151 lines. |
| **model-eval** | `[ verified ]` | Qwen 3 14B evaluated (85.26%) vs Qwen 2.5 14B (89.47%) — current model stays. |
| **narrative-extraction** | `[ verified ]` | Phase 1 complete (849c664f): Pass 3b ungated from Pass 1 classifier, announcement_type persisted in Document + Qdrant, context 4K→8K, commentary chunks get 150-char overlap, analysis modules consume guidance_summary + material_changes. Phase 2 (section-aware chunking, type-specific extractors) deferred pending evidence from ungated extraction. |
| **docs-governance** | `[ in-progress ]` | Root startup docs aligned to the canonical backend entrypoint. Repository-audit instructions updated to use actual repo manifests. Backend API surface, extraction, embeddings, routing, scripts index, portfolio module docs, Cockpit control-plane docs, and eval-fixture architecture docs refreshed. Open item: Cockpit contract/code mismatch still needs an explicit architecture decision. |

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
| 849c664f | narrative-extraction | Phase 1: Ungate Pass 3b from financial classifier, persist announcement_type (Document + Qdrant), context 4K→8K, commentary chunk overlap, analysis modules consume guidance_summary + material_changes. 365 tests passing. |
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

---

## Backlog (scoped but not started)

- ~~**Watchlist trigger mechanism**~~ — SHIPPED: `/watch scan`, `scan_watchlist` tool, `WatchlistTrigger` orchestrator
- **Narrative extraction Phase 2** — evidence-driven: section-aware chunking, type-specific extractors for ops/governance/investor docs, expanded narrative schema. Depends on data from Phase 1 ungated extraction.
- **Transcript enrichment Phase 3** — speaker-turn parsing, temporal anchoring, multi-pass memo extraction (full transcript instead of 12K truncation)
- **Sentiment scoring layer** — quantify narrative sentiment across news/transcripts
- **Alert thresholds from strategy** — replace hardcoded thresholds in alerts.py with user-defined strategy criteria
- **FX conversion logic** — build actual currency conversion; policy defined in `docs/architecture/16_currency_and_fx_policy.md`; blocked on product decision about which conversion source to use
- **Scrapling integration** — status unknown; see `docs/ops/scrapling_integration_note.md`
- **Recovery/reconstruction integration** — status unknown; see `docs/ops/recovery_reconstruction_integration_manifest.md`
