# STATE.md — Active Work Tracker

> **Purpose:** Single source of truth for what is planned, in-flight, verified, and shipped.
> Update this file at the end of every session alongside the milestone commit.
> For detailed context on any item, follow the linked doc or run `git log --oneline`.

Last updated: 2026-03-24 (session 4 — live eval)
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
| **extraction-hardening** | `[ in-progress ]` | (1) FX conversion logic not yet built — policy defined, ok_low_confidence stands; (2) provenance query UX: inspect script exists, schema access still awkward. (3) Live eval never run — critical gap documented. Quarterly CF values hand-verified (b78b2964). |
| **news-pipeline** | `[ verified ]` | Embedding routing fixed, asx_docs rebuilt at 768-dim (a4564e47) |
| **eval-fixtures** | `[ verified ]` | Quarterly GRE fixture + SEG non-mining fixture promoted (b78b2964). MIN values confirmed via docling cache. Quality assessment doc written. |
| **extraction-quality** | `[ in-progress ]` | Live eval run 1 complete: 58.3% overall (Mistral 7B, 3 confounders). JSON parentheses bug fixed. Open: (1) Docling cache build for BHP/EQR in progress; (2) re-run with Qwen 2.5 14B after cache ready. Report at docs/claude/extraction_quality_assessment.md |

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
| (this session) | extraction-quality | Live eval run 1: 58.3% overall (Mistral 7B, 3 confounders). JSON parentheses bug fixed + 3 tests. Docling cache build for BHP/EQR initiated. |
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
