# Session Handoff — strategy-system-improvements (2026-03-31)

**Branch:** `cloud/session-20260319`

---

## What was built this session

### 1. Sector Comparison Module (NEW)
**File:** `backend/app/services/analysis/sector_comparison.py` (16KB)
- 10 GICS sector mappings with 150+ ASX tickers
- `compute_sector_stats()` — median PE, FCF yield, revenue growth, EBIT margin per sector
- `compare_to_sector()` — percentile ranking + human-readable labels ("cheap", "above average")
- 24-hour TTL cache via `get_sector_stats_cached()`
- Lazy imports to avoid `__init__.py` package chain issue

### 2. Signal Engine — Sector-Relative Scoring
**File:** `cockpit/core/research/signal_engine.py` (modified)
- `TickerScorer.score()` now computes sector comparison when ticker is in sector mapping
- Valuation sub-score blended: 40% absolute + 60% sector-relative
- Return dict includes `sector_comparison` field with percentiles
- Configurable weights via `StrategyService.get_signal_weights()`

### 3. Thesis Auto-Invalidation
**File:** `cockpit/core/research/thesis.py` (modified)
- `auto_evaluate()` — invalidates when disconfirming >= 2x supporting OR disconfirming >= 3 with 0 supporting
- `expire_stale(days=90)` — marks old active theses as "expired"
- `add_evidence()` calls `auto_evaluate()` after adding disconfirming evidence
- `VALID_STATUSES` now includes "expired"

### 4. Auto-Reflection in Watchlist Scanner
**File:** `worker/worker_app/research_tasks.py` (modified)
- After scanning tickers, runs `ThesisService.expire_stale(90)`
- Runs `ReflectionService.review_open_decisions()` + `reflect_and_learn()` for decisions > 30 days
- Returns `expired_theses` and `reflections` counts in task result

### 5. Tool Routing Guide
**File:** `cockpit/core/chat.py` (modified)
- `_build_system_instruction()` now appends `## Tool Selection Guide` to system prompt
- Covers 5 categories: quick lookups, analysis, strategy, monitoring, research
- Includes tool dependency hints ("score before creating thesis")

### 6. Configurable Signal Weights
**Files:** `strategy.py`, `signal_engine.py`, `tool_definitions.py`, `tool_executor.py`, `app.py`
- `StrategyService.get_signal_weights()` / `set_signal_weights(weights)` — reads/writes from `user_preferences`
- `adjust_signal_weights` mutating tool (validates sum ≈ 1.0)
- Confirm handler in `app.py` for `/confirm` flow
- `TickerScorer` resolves weights from strategy service, falls back to defaults

### 7. Commentary in Deep Research
**File:** `cockpit/core/research/deep_research.py` (modified)
- Added RAG query for `source="company"` commentary chunks (investor letters, transcripts)
- Provides qualitative context alongside quantitative data in synthesis

### 8. Bugfix: app.py missing logger
**File:** `cockpit/ui/app.py` (modified)
- Added `import logging` and `logger = logging.getLogger(__name__)` — was undefined

## Files Changed

| File | Type | Changes |
|------|------|---------|
| `backend/app/services/analysis/sector_comparison.py` | NEW | Sector comparison module |
| `cockpit/core/research/signal_engine.py` | Modified | Sector-relative scoring + configurable weights |
| `cockpit/core/research/thesis.py` | Modified | auto_evaluate + expire_stale + "expired" status |
| `cockpit/core/research/deep_research.py` | Modified | Commentary RAG retrieval |
| `cockpit/core/chat.py` | Modified | Tool routing guide in system prompt + strategy_service wiring |
| `cockpit/core/strategy.py` | Modified | get/set_signal_weights methods |
| `cockpit/core/tool_definitions.py` | Modified | +adjust_signal_weights tool (38 total) |
| `cockpit/core/tool_executor.py` | Modified | +adjust_signal_weights handler/proposal |
| `cockpit/ui/app.py` | Modified | +logger import, +weight adjustment confirm handler |
| `worker/worker_app/research_tasks.py` | Modified | +thesis expiration + auto-reflection |

## Verification

- All files lint clean (ruff check)
- All imports verified (38 tools, 13 mutating)
- ThesisService.auto_evaluate + expire_stale confirmed
- StrategyService.get_signal_weights + set_signal_weights confirmed
- Sector comparison lazy import pattern verified (avoids __init__.py chain)

## Resume command

Read HANDOFF.md. For live testing: run cockpit with `COCKPIT_AGENT_MODE=structured`.
Try: `score_ticker("BHP")` — should return composite score with sector comparison.
Try: `screen_tickers(["BHP","CSL","WDS"])` — ranked with sector-relative valuation.
Try: `adjust_signal_weights(health=0.5, momentum=0.2, valuation=0.2, technical=0.1)`.
