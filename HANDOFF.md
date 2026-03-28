# Session Handoff — strategy-schema-with-sources (2026-03-28)

**Branch:** cloud/session-20260319
**Worktree:** /home/l4nd0/tenn (main working tree)

---

## Completed This Session

### Part 1 — Strategy Workshopping Schema (d173a8da)
- `global_strategy` + `ticker_strategy` tables in Cockpit SQLite (additive)
- `StrategyService`: add/get/delete criteria, record decisions, build LLM context block
- Strategy context injected into analysis above dossier findings, framed as evaluation criteria
- `/strategy list|add|decide|delete` commands
- Natural language: "what is my strategy", "what do I think about `<TICKER>`", "set my decision on `<TICKER>`"
- 10 tests, all passing

### Part 2 — Evidence Sourcing (2e9c3ddb)
- `SourcesFormatter`: compact footer showing RAG hits (top 3 with scores), financial periods, dossier/strategy counts
- Sources metadata collected in `gather_local_context()` payload
- Footer appended to analysis responses in TUI (display-only)
- `/sources on|off` toggles `show_sources` preference (persists in SQLite, default ON)
- 6 tests, all passing

### Test Results
- Cockpit: **270 passed**, 1 skipped
- Backend: **314 passed**, 3 pre-existing failures (share_capital, qdrant_resolution x2)
- Lint: clean

---

## TUI Verification Status

**Still pending** — Stacks A through D require interactive Cockpit TUI session.

- **Stack A** (cockpit-memory-wiring): dossier injection, watchlist commands
- **Stack B** (transcript-approval-gate): /review commands
- **Stack C** (strategy-schema): /strategy commands, context injection
- **Stack D** (evidence-sourcing): sources footer display, /sources toggle

---

## Remaining Narrative Vertical Work

1. **Sentiment scoring layer** — quantify narrative sentiment across news/transcripts
2. **Watchlist trigger mechanism** — depends on strategy schema (now complete)
3. **Alert thresholds from strategy** — replace hardcoded thresholds in alerts.py

---

## Parallel Pending Sessions

- `research-test-coverage` — coverage gaps in research system tests
- `ANZ regression` — banking EBIT extraction accuracy
- `test_skip_share_capital` — pre-existing test failure in backend

---

## Uncommitted Changes (pre-existing, not from this session)

- `.claude/monitors/bug_registry.json`
- `financial-engine_v2/backend/tests/eval_config.json`
- `financial-engine_v2/reports/extraction_baseline.json`

---

## Resume Command

```
Read HANDOFF.md — next narrative session is watchlist trigger mechanism OR sentiment scoring layer.
TUI verification (Stacks A-D) is still pending.
```
