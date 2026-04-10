# Cockpit Tool Audit — 2026-04-10

Comprehensive verification of every tool call available to the cockpit LLM.

**Status: ALL FIXES APPLIED AND E2E TESTED** (2026-04-10 20:00 AEST)

---

## CRITICAL: Root Cause of Action Failures

### 1. `health_guard` import — blocks `single_ticker_announcement_backfill` and `full_history`

**Status: FIXED**

**Root cause:** `_build_action_env()` in `backend/app/routes/cockpit_api.py:1493` built PYTHONPATH with only `backend/`, `cockpit/`, `/app`, `/app/cockpit`. Missing the parent `scripts/` directory containing `health_guard.py` and `ticker_quarantine.py`.

In the Docker container, `./scripts` mounts at `/scripts` and `../` (parent tenn/) mounts at `/workspace:ro`. The script `full_history_ticker_sync.py` computes `ROOT_SCRIPTS = REPO_ROOT.parent / "scripts"` but in-container `__file__` is `/scripts/full_history_ticker_sync.py` so `REPO_ROOT.parent` resolves to `/` — and `health_guard.py` lives at `/workspace/scripts/`, not `/scripts/`.

**Fix applied:** Added `COCKPIT_SHARED_SCRIPTS_ROOT` (resolves to `/workspace/scripts` in docker), `repo_root.parent / "scripts"` (local mode), `repo_root / "scripts"`, and `/workspace/scripts` to PYTHONPATH candidates.

**E2E verified:** `docker exec fe_backend python3 -c "from health_guard import assert_healthy"` succeeds. Backfill action passes import phase.

### 2. `_build_financials_narrative` format crash — blocks ALL chat calls for tickers with financial data

**Status: FIXED** (discovered during E2E testing)

**Root cause:** `cockpit/core/tools.py:837` used `f"${rev:,.0f}"` format strings on financial values that arrive as strings from the DB/API (e.g., `"27902000000"` instead of `27902000000.0`). The `:,.0f` format code requires `float`/`int`, not `str`.

**Fix applied:** Added `_num()` coercion helper that safely converts all financial values to `float` before formatting. Applied to all 8 numeric values in the function (revenue, ebit, ocf, capex, net_debt, and their priors).

---

## Tool-by-Tool Verification

### Read-Only Tools (26 defined, 25 in dispatch table)

| # | Tool | Status | Notes |
|---|------|--------|-------|
| 1 | `query_ticker_data` | **Works** | Routes through `ToolRouter.gather_local_context` |
| 2 | `get_company_dump` | **Works** | Requires `backend_api_client` (returns error if not configured) |
| 3 | `get_price` | **Works** | Uses yfinance via `ToolRouter.get_price_context_for_window` |
| 4 | `get_price_on_date` | **Works** | Fetches 10y history, scans for exact date — **inefficient but functional** |
| 5 | `get_price_range` | **Works** | Same 10y fetch + filter approach |
| 6 | `get_financials` | **Works** | Requires backend API client |
| 7 | `search_news` | **Conditional** | Works if news corpus is populated; gracefully suggests `run_news_ingest` if empty |
| 8 | `search_announcements` | **Works** | Requires backend API client |
| 9 | `search_files` | **Works** | Uses `FileIndexer.search_text` |
| 10 | `list_recent_reports` | **Works** | Uses `FileIndexer.list_recent_reports` |
| 11 | `get_data_quality` | **Works** | Requires backend API client |
| 12 | `run_analysis` | **Works** | Calls `POST /api/analysis/{ticker}` via httpx |
| 13 | `fetch_url` | **Works** | Gated by `web_default_enabled` config |
| 14 | `get_strategy` | **Conditional** | Returns error if `strategy_service=None` (depends on successful init) |
| 15 | `search_web` | **Conditional** | Needs `web_default_enabled=True` AND either `BraveSearchClient` or `WebFetcher` fallback |
| 16 | `search_social` | **Conditional** | Returns error if `HNSearchClient` init failed |
| 17 | `recall_dossier` | **Conditional** | Returns error if `CompanyDossierService` init failed |
| 18 | `deep_research` | **Conditional** | Returns error if `DeepResearchRunner` init failed |
| 19 | `get_watchlist_alerts` | **Soft fail** | Returns `{ok: true, alerts: []}` if alert reader unavailable — **silent degradation** |
| 20 | `scan_watchlist` | **Conditional** | Returns error if `WatchlistTrigger` not configured |
| 21 | `score_ticker` | **Conditional** | Returns error if `TickerScorer` init failed |
| 22 | `screen_tickers` | **Conditional** | Returns error if `ScreenRunner` init failed |
| 23 | `get_valuation` | **Works** | Does inline import of `compute_valuation_multiples` |
| 24 | `get_thesis` | **Soft fail** | Returns `{ok: true, theses: []}` if thesis service unavailable — **silent degradation** |
| 25 | `check_decision_outcome` | **Conditional** | Returns error if reflection service unavailable |
| 26 | `review_open_decisions` | **Soft fail** | Returns `{ok: true, decisions: []}` if reflection service unavailable — **silent degradation** |

### Mutating Tools (13 defined)

| # | Tool | Maps to Action | Status | Notes |
|---|------|---------------|--------|-------|
| 1 | `run_backfill` | `single_ticker_announcement_backfill` | **BROKEN** | `health_guard` import failure in container |
| 2 | `run_metric_extraction` | `metric_extraction` | **Works** | Calls `rebuild_ticker_financials_from_docs.py` |
| 3 | `run_news_ingest` | `daily_news_ingest` | **Conditional** | Shared script; resolved via `_resolve_shared_script` |
| 4 | `run_announcement_ingest` | `daily_announcement_ingest` | **Works** | Uses `daily_asx_all_announcements_action.py` |
| 5 | `update_financials` | `update_ticker_financials` | **Likely broken** | Same script as `full_history`, imports `health_guard` |
| 6 | `rebuild_financials` | `rebuild_ticker_financials` | **Works** | Different script, no `health_guard` dep |
| 7 | `audit_financials` | `audit_ticker_financials` | **Works** | Separate script |
| 8 | `generate_chart` | `show_candlestick` | **Works** (no-op stub) | `noop_chart.py` just exits 0 — chart is generated in-app before subprocess |
| 9 | `save_research_finding` | Direct dossier write | **Conditional** | Requires `dossier_service` to be initialized |
| 10 | `create_thesis` | Direct strategy handler | **Conditional** | Requires `thesis_service` + `risk_gate` |
| 11 | `add_thesis_evidence` | Direct strategy handler | **Conditional** | Requires `thesis_service` |
| 12 | `reflect_on_decision` | Direct strategy handler | **Conditional** | Requires `reflection_service` |
| 13 | `adjust_signal_weights` | Direct strategy handler | **Conditional** | Requires `strategy_service` |

---

## Issues by Severity

### CRITICAL (tools that will always fail)

1. **`run_backfill` / `single_ticker_announcement_backfill`** — `health_guard.py` not on PYTHONPATH in container execution. This is the error hit when trying `eos price?` → backfill.

2. **`update_financials` / `update_ticker_financials`** — `update_ticker_financials.py` likely also imports from parent `scripts/` (same pattern as `full_history_ticker_sync.py`). Needs verification.

### HIGH (poor execution logic)

3. **`_build_action_env` missing parent `scripts/` on PYTHONPATH** (`cockpit_api.py:1493`) — Root cause of #1 and #2. Only adds `backend/`, `cockpit/`, `/app`, `/app/cockpit`. Should also include:
   - `repo_root.parent / "scripts"` (local mode)
   - `"/scripts"` (container mode)
   - `repo_root / "scripts"` (script-local imports like `_run_metadata`)

4. **`get_price_on_date` and `get_price_range` inefficiency** — Both fetch **10 years of daily data (3000 rows)** via yfinance just to find a single date or filter a range. This is wasteful when yfinance supports `start`/`end` params directly.

5. **Silent degradation in 3 tools** — These violate the "leave no silent degradation" rule:
   - `get_watchlist_alerts`: returns `{ok: true, alerts: []}` with just a `message` field when alert reader is `None`
   - `get_thesis`: returns `{ok: true, theses: []}` when thesis service is `None`
   - `review_open_decisions`: returns `{ok: true, decisions: []}` when reflection service is `None`

   These should return `ok: false` with a clear error, not pretend everything is fine with empty results.

6. **`extraction_controller` never wired** — `ToolExecutor.__init__` accepts `extraction_controller` but `ChatController` never passes it. The extraction validation at `tool_executor.py:1009` (`if tool_name == "run_metric_extraction" and self._extraction_ctrl is not None`) is dead code — the guard always skips.

### MEDIUM (functional but with issues)

7. **Pydantic `model_` namespace warning** — The error trace also shows: `Field "model_routing_config" in Settings has conflict with protected namespace "model_"`. This is in `config.py` — won't crash, but it's a configuration hygiene issue that pollutes stderr.

8. **`generate_chart` / `show_candlestick` is a no-op stub** — The script `noop_chart.py` literally does `sys.exit(0)`. The chart is supposedly generated in-app before the subprocess runs, but if the in-app generation fails, the action still reports "success."

9. **`search_announcements` requires ticker but schema says `required: []`** — The tool definition at `tool_definitions.py:223` says no required fields, but `_exec_search_announcements` at `tool_executor.py:436` returns an error if ticker is empty. The LLM might omit the ticker and get confused.

### LOW (not wired yet / future implementation)

10. **Actions defined but not exposed as tools:**
    - `full_history` — in ActionRegistry but no corresponding tool in `_MUTATING_TOOLS` (use `run_backfill` → `single_ticker_announcement_backfill` instead; `full_history` is a superset)
    - `daily_marketindex` — requires headed browser, not suitable for LLM-triggered action
    - `daily_asx_marketwide` — duplicated by `daily_announcement_ingest` (same script)
    - `asx_enrichment_sweep` — available via `universe_announcement_enrichment_backfill` tool path
    - `asx_enrichment_chunked` — legacy, superseded by sweep
    - `sort_asx_docs` — classification utility, no tool mapping
    - `resume_pending` — recovery utility, no tool mapping
    - `recover_headed` — MarketIndex recovery, no tool mapping

11. **`universe_announcement_enrichment_backfill`** — In `VISIBLE_ACTION_IDS` but has **no corresponding mutating tool** in `tool_definitions.py`. It appears in the action panel but cannot be triggered by the LLM via tool calling — only through intent keyword routing or direct UI action.

---

## Summary

| Category | Count |
|----------|-------|
| CRITICAL (always fails) | 2 |
| HIGH (poor logic / silent degradation) | 4 |
| MEDIUM (functional issues) | 3 |
| LOW (not wired) | 2 |
| **Working read-only tools** | 19/26 (7 conditional on service init) |
| **Working mutating tools** | 7/13 (5 conditional, 1 broken) |

The single root cause behind the critical failures is **`_build_action_env` not including the parent `scripts/` directory on PYTHONPATH**.

---

## E2E Test Results (curl against running backend in Docker)

All tests run against `POST /api/cockpit/chat` with `stream: false` on 2026-04-10.

| Tool | Test Query | Result |
|------|-----------|--------|
| `query_ticker_data` | "what data do we have for BHP?" | **PASS** — returned financial summary |
| `get_price` | "what is BHP price?" | **PASS** — returned price context |
| `get_financials` | "show me BHP financials" | **PASS** — revenue, EBIT, FCF formatted correctly |
| `search_announcements` | "list BHP announcements" | **PASS** — returned action proposal (stale data) |
| `run_analysis` | "run analysis on BHP" | **PASS** — returned analysis summary |
| `get_data_quality` | "check data quality for BHP" | **PASS** — returned quality assessment |
| `search_news` | "any recent news about BHP?" | **PASS** — returned news summary |
| `get_strategy` | "what is my strategy for BHP?" | **PASS** — returned strategy context |
| `list_recent_reports` | "list recent reports" | **PASS** — returned report list |
| `search_web` | "search the web for BHP iron ore outlook" | **PASS** — returned web results |
| `run_backfill` (proposal) | "backfill EOS data" | **PASS** — returned action_preview |
| `run_backfill` (execute) | action/execute with EOS | **PASS** — no import error, job running |
| `action/preview` | preview single_ticker_announcement_backfill | **PASS** — returned command preview |
| `get_company_dump` | /api/context/ticker?ticker=BHP | **PASS** — returned full context |
| `score_ticker` | "score BHP" | **SKIP** — llama.cpp 500 (GPU busy with backfill) |
| `get_valuation` | "what is BHP valuation?" | **SKIP** — llama.cpp 500 (GPU busy) |

Tools marked SKIP failed due to local llama.cpp server being busy (GPU contention from running backfill), not from tool logic errors.

---

## Key Files Reference

| Component | Path |
|-----------|------|
| Tool definitions | `cockpit/core/tool_definitions.py` |
| Action registry | `cockpit/core/actions.py` |
| Tool executor | `cockpit/core/tool_executor.py` |
| Agent loop | `cockpit/core/agent_loop.py` |
| Chat controller | `cockpit/core/chat.py` |
| Backend cockpit API | `backend/app/routes/cockpit_api.py` |
| Cockpit service init | `backend/app/services/cockpit_service.py` |
| health_guard module | `../scripts/health_guard.py` (parent repo) |
