# Cockpit Autonomous Research System — Testing Guide

> Orchestrator brief for live testing the research system in the cockpit TUI.

## Prerequisites

1. **Backend running** at `:8000` — `bash financial-engine_v2/scripts/run_local_backend.sh`
2. **LLM serving** — llama.cpp at `:8001` (chat model) or `ANTHROPIC_API_KEY` set
3. **Environment** — `COCKPIT_AGENT_MODE=structured` (default)
4. **Optional** — `BRAVE_SEARCH_API_KEY` for Brave web search (falls back to DuckDuckGo without it)
5. **Optional** — Redis + Celery for watchlist scanner (not needed for manual testing)

## What Was Built

7 new tools added to the cockpit agent loop (25 total, was 19):

| Tool | Type | What it does |
|------|------|-------------|
| `search_web` | read-only | Brave Search API → structured results (title, url, snippet). Falls back to DuckDuckGo. |
| `search_social` | read-only | HN Algolia API → stories sorted by points. Free, no auth. |
| `recall_dossier` | read-only | Retrieves accumulated research findings for a ticker from `~/.tenn/memory/dossiers/`. |
| `save_research_finding` | **mutating** | Persists a finding to the company dossier. Requires user confirmation. |
| `deep_research` | read-only | Meta-tool: gathers financials + price + web + HN + announcements + prior dossier, synthesizes via LLM in a **separate context**, auto-saves to dossier. Bypasses 6-iteration loop limit. |
| `get_watchlist_alerts` | read-only | Surfaces alerts from the background watchlist scanner at `~/.tenn/memory/alerts/`. |

## Test Plan

### Test 1: Web Search (search_web)

**Prompt:** `"Search the web for recent BHP news"`

**Expected behavior:**
- Agent calls `search_web(query="BHP news")`
- Returns structured results with titles, URLs, snippets
- If `BRAVE_SEARCH_API_KEY` set → Brave results. If not → DuckDuckGo fallback.
- Agent summarizes the results in natural language

**Verify:** Tool call appears in agent loop output. Results contain real URLs.

---

### Test 2: Social Search (search_social)

**Prompt:** `"What is Hacker News saying about lithium mining?"`

**Expected behavior:**
- Agent calls `search_social(query="lithium mining")`
- Returns HN stories sorted by points (title, url, points, num_comments)
- Agent synthesizes the discussion themes

**Verify:** Stories have real HN URLs and point counts > 0.

---

### Test 3: Deep Research (deep_research)

**Prompt:** `"Do deep research on BHP"`

**Expected behavior:**
- Agent calls `deep_research(ticker="BHP")`
- DeepResearchRunner internally:
  1. Queries financials from local DB
  2. Fetches 6-month price history
  3. Searches web for "BHP ASX news"
  4. Searches HN for "BHP"
  5. Checks announcements in DB
  6. Recalls prior dossier entries
  7. Synthesizes via LLM (separate context)
  8. Auto-saves to `~/.tenn/memory/dossiers/BHP.jsonl`
- Returns structured brief: summary, key_metrics, sentiment, risks, catalysts
- Agent presents the brief to user

**Verify:**
- `~/.tenn/memory/dossiers/BHP.jsonl` created with at least one entry
- Log shows "deep_research: gathered N sources for BHP"
- Brief contains real data from DB (not hallucinated)

---

### Test 4: Dossier Recall (recall_dossier)

**Prompt** (after Test 3): `"What do you know about BHP from past research?"`

**Expected behavior:**
- Agent calls `recall_dossier(ticker="BHP")`
- Returns the finding saved by `deep_research` in Test 3
- Agent presents the accumulated knowledge

**Verify:** The recalled finding matches what was synthesized in Test 3.

---

### Test 5: Save Research Finding (save_research_finding)

**Prompt:** `"Save this finding: BHP's iron ore division is facing headwinds from declining Chinese steel demand"`

**Expected behavior:**
- Agent calls `save_research_finding(ticker="BHP", finding="...", source="user_analysis")`
- **Confirmation prompt appears** (mutating tool)
- User confirms → finding appended to `~/.tenn/memory/dossiers/BHP.jsonl`

**Verify:** Confirmation gate fires. After approval, `BHP.jsonl` has a new entry.

---

### Test 6: Focused Deep Research

**Prompt:** `"Research WDS with a focus on valuation"`

**Expected behavior:**
- Agent calls `deep_research(ticker="WDS", focus="valuation")`
- Synthesis is weighted toward valuation metrics
- Auto-saves to `~/.tenn/memory/dossiers/WDS.jsonl`

---

### Test 7: Watchlist Alerts (get_watchlist_alerts)

**Prompt:** `"Any alerts from the watchlist scanner?"`

**Expected behavior without Celery:**
- Agent calls `get_watchlist_alerts(since_hours=24)`
- Returns empty alerts (scanner hasn't run)
- Agent reports "no recent alerts"

**To test with alerts:** Manually create an alert:
```python
from cockpit.core.research.alerts import AlertReader
AlertReader.write_alert(ticker="BHP", alert_type="price_move", message="BHP up 4.2% since last scan", data={"change_pct": 0.042})
```
Then re-run the prompt — should surface the alert.

---

## Activation for Background Scanner (optional)

```bash
# 1. Create watchlist
mkdir -p ~/.tenn/state
echo '["BHP","CSL","WDS","RIO","FMG"]' > ~/.tenn/state/watchlist.json

# 2. Start Celery worker + beat (from financial-engine_v2/worker/)
cd financial-engine_v2/worker
PYTHONPATH=.:.. ../.venv/bin/celery -A worker_app worker -B -l info

# 3. Or trigger manually
PYTHONPATH=.:.. ../.venv/bin/celery -A worker_app call watchlist_research_scan
```

Scanner runs at 8am/12pm/4pm AEST. Alerts appear in `~/.tenn/memory/alerts/pending.jsonl`.

---

## Data Locations

| Data | Path |
|------|------|
| Company dossiers | `~/.tenn/memory/dossiers/<TICKER>.jsonl` |
| Situation memory | `~/.tenn/memory/situations.jsonl` |
| Watchlist alerts | `~/.tenn/memory/alerts/pending.jsonl` |
| Scanner state | `~/.tenn/memory/research_scan_state.json` |
| Watchlist config | `~/.tenn/state/watchlist.json` |

## Architecture Notes

- **DeepResearchRunner** uses a **separate LLM context** from the agent loop. It calls `HybridRouter.complete()` directly with its own message list. This means the 12K token budget of the agent loop is not consumed by deep research.
- **Dossier** is agent scratch memory (JSONL files), not system truth. No DB schema changes. Compliant with SYSTEM_CONTRACT §1.2.
- **Fallback chain**: Brave → DuckDuckGo (web search), BM25 → keyword matching (situation memory).
- **Tool count**: 25 total (18 read-only + 7 mutating). The system prompt includes all tool schemas (~10.5K chars).
