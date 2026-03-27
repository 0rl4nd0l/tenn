# STATE.md — Active Work Tracker

> **Purpose:** Single source of truth for what is planned, in-flight, verified, and shipped.
> Update this file at the end of every session alongside the milestone commit.
> For detailed context on any item, follow the linked doc or run `git log --oneline`.

Last updated: 2026-03-27 (sessions — GPU process management rails + eval 89.47% PASS + L022/L023 logged)
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
| **eval-fixtures** | `[ verified ]` | 9 fixtures live-validated 2026-03-27. AZJ threshold=0.0, BHP/RMS configs added. 88.64% excl. AZJ = at baseline. |
| **extraction-quality** | `[ in-progress ]` | 88.64% accuracy on 8 fixtures (excl. AZJ). Docling restored as default (877a8203). ANZ 72.7% — banking revenue format regression to investigate. |
| **extraction-perf** | `[ verified ]` | Docling default restored (877a8203). PyMuPDF available via EXTRACTION_BACKEND=pymupdf. |
| **cockpit-agent** | `[ verified ]` | Agent mode + ToolExecutor verified via Textual Pilot 2026-03-27: all 7 checks PASS, 217 unit tests. |
| **gpu-process-rails** | `[ verified ]` | Canonical port manifest (§9.4), agent spawn protocol (§9.5), `gpu_process_guard.sh`, `llamacpp_manager.py` topology check. L022 logged. |

---

## Pipeline Build Status

From [docs/architecture/14_roadmap_and_modules.md](../architecture/14_roadmap_and_modules.md).

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| 1. Data acquisition | Filings, news, prices, fundamentals | `[ in-progress ]` | Filings + news operational; prices and fundamentals coverage incomplete |
| 2. Retrieval (RAG) | `POST /rag/query` — semantic search over ingested docs | `[ verified ]` | Operational; news_chunks resynced with relevance-ordered tickers |
| 3. Analysis modules | Risk, valuation, moat, catalysts, ROIC, balance sheet | `[ planned ]` | Not yet built; module contracts defined in roadmap doc |
| 4. Portfolio module | Exposure, correlation, position sizing | `[ planned ]` | Not yet built |
| 5. Outputs | Artifacts written under `reports/` | `[ in-progress ]` | Directory structure exists; per-analysis-module artifacts not yet wired |

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
| 3d | CI workflow (GitHub Actions) | `[ planned ]` — only when Actions is formally adopted |

---

## Recently Shipped Milestones

| Commit | Workstream | Summary |
|--------|------------|---------|
| (this session) | gpu-process-rails | GPU process management: `gpu_process_guard.sh`, `llamacpp_manager.py` topology check, SYSTEM_CONTRACT §9.4+§9.5, CLAUDE.md pre-flight GPU field, L022+L023. Eval 89.47% PASS. |
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

- **FX conversion logic** — build actual currency conversion; policy defined in `docs/architecture/16_currency_and_fx_policy.md`; blocked on product decision about which conversion source to use
- **Analysis modules (Phase 3)** — risk, valuation, moat, catalysts, ROIC, balance sheet; contracts in `14_roadmap_and_modules.md`
- **Portfolio module (Phase 4)** — exposure, correlation, position sizing
- **Scrapling integration** — status unknown; see `docs/ops/scrapling_integration_note.md`
- **Recovery/reconstruction integration** — status unknown; see `docs/ops/recovery_reconstruction_integration_manifest.md`
