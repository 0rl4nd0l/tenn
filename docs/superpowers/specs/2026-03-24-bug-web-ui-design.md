# Bug Monitor Web UI — Design Spec

**Date:** 2026-03-24
**Status:** Approved
**File in scope:** `.claude/monitors/bug_web_ui.py`

---

## Context

`bug_web_ui.py` is a self-contained Python `http.server` dashboard that reads `.claude/monitors/alerts.log` (written by `monitor_agents.py`, which runs 5 Claude API monitoring agents in parallel threads). The file already contains:

- A `KNOWN_FIXES` dict with 4 pre-loaded bugs (explanation, A/B agent debate, proposed diff, verdict)
- A full dark-theme HTML/JS frontend with bug cards, collapsible tabs (Explanation / Agent Debate / Proposed Fix), diff syntax highlighting, and a "Deploy Fix Agent" button
- A `GET /api/data` endpoint that merges live alerts with `KNOWN_FIXES`
- `POST /api/deploy/<fix_id>` handlers that apply **hardcoded string-replacement patches** (not real agents)

**Goal:** Replace the hardcoded deploy handlers with real `claude` CLI subprocess invocations, and add on-demand A/B debate generation via the Anthropic Messages API for dynamically detected bugs that have no pre-loaded fix.

---

## Architecture

The `http.server.HTTPServer` base is retained. No migration to FastAPI. Three new capabilities are added to the existing server:

### 1. On-Demand Debate — `POST /api/debate/<issue_id>`

For alerts without a `KNOWN_FIXES` entry, generates a live A/B agent debate using the Anthropic Messages API.

**Input:** `issue_id` (URL path), request body JSON: `{agent, severity, issues: [{type, location, detail}]}`
**Output:** `{agent_a: {name, approach, diff}, agent_b: {name, approach, diff}, verdict, winning_agent}`

**Flow:**
1. Check `debates.json` — return cached result if present (avoid re-paying API cost)
2. Build a prompt with: issue detail, file path, agent type (BUGS / SECURITY / etc.), severity
3. Call `anthropic.Anthropic().messages.create(model="claude-sonnet-4-6", max_tokens=2048, ...)`
4. Parse the JSON response into the debate schema
5. Write result to `debates.json` keyed by `issue_id`
6. Return the debate object

**Error cases:**
- `ANTHROPIC_API_KEY` not set → `{ok: false, message: "ANTHROPIC_API_KEY not set"}`
- JSON parse failure → `{ok: false, message: "Model response was not valid JSON: <raw[:300]>"}`
- Network/API error → `{ok: false, message: "<exception str>"}`

### 2. Claude Agent Deploy — `POST /api/deploy/<fix_id>`

Replaces all hardcoded `_fix_*` methods with a single subprocess-based dispatcher.

**Flow:**
1. Check `which claude` — return error immediately if not on PATH
2. Construct task description from `KNOWN_FIXES` entry or cached debate in `debates.json`
3. Spawn subprocess in a background `threading.Thread`:
   ```
   claude --allowedTools Edit,Read,Bash,Glob,Grep --print --output-format json -p "<task>"
   ```
4. Register job: `JOBS[fix_id] = {status: "running", output: [], exit_code: None}`
5. Worker thread reads stdout line-by-line, appending to `JOBS[fix_id]["output"]`
6. On completion: set `status: "done"` or `status: "error"` + `exit_code`
7. Timeout: if subprocess exceeds 300s, kill and set `status: "error"` with message
8. Return immediately: `{ok: true, status: "running"}`

**Threading safety:** `JOBS` dict is guarded with `threading.Lock()`.

### 3. Job Status Poll — `GET /api/job/<fix_id>`

**Output:** `{status: "running"|"done"|"error", output: "<accumulated stdout>", exit_code: int|null}`

Frontend polls every 1500ms until `status != "running"`.

---

## Frontend Changes

Three additions to the existing JavaScript (no HTML structure changes):

### `loadDebate(issueId, itemData)`
- Called when a bug card without a known fix is expanded for the first time (lazy — not on page load)
- Shows "Generating debate…" spinner in the bug body
- POSTs to `/api/debate/<issueId>` with the alert data as JSON body
- On success: re-renders the card body with full Explanation / Agent Debate / Proposed Fix tabs (same template as known fixes)
- On error: shows error message in card body

### Updated `deployFix(fixId, btn)`
- After POSTing `/api/deploy/<fixId>`, switch to polling loop
- Every 1500ms: GET `/api/job/<fixId>`, append new output lines to `#output-<fixId>`
- Stop polling when `status != "running"`
- On `done`: button → "✓ Fix Applied", green
- On `error`: button → "↺ Retry", re-enabled

### "Get AI Analysis" button
- Added to the single "Issue" tab for alerts without a known fix
- Clicking triggers `loadDebate(issueId, itemData)` once
- After debate loads, the button is replaced by the full tab bar

---

## Data Files

| File | Purpose |
|------|---------|
| `.claude/monitors/alerts.log` | Written by `monitor_agents.py` — read-only input |
| `.claude/monitors/debates.json` | Written by on-demand debate endpoint — persists generated debates |
| `.claude/monitors/KNOWN_FIXES` | In-memory Python dict in `bug_web_ui.py` — pre-loaded bug analyses |

`JOBS` dict is in-memory only (lost on server restart — acceptable since jobs complete in <5 min).

---

## Constraints

- **Scope:** Only `bug_web_ui.py` is modified. No changes to `monitor_agents.py`, `alerts.log` format, or the `KNOWN_FIXES` data structure.
- **No new files** created (except `debates.json` at runtime).
- `http.server.HTTPServer` is retained — no FastAPI migration.
- The `claude` CLI must be on PATH for the deploy feature to work (soft dependency — degrades gracefully with a clear error).
- `ANTHROPIC_API_KEY` must be set for on-demand debate (same requirement as `monitor_agents.py`).

---

## Out of Scope

- Streaming agent output via SSE (polling is sufficient for this use case)
- Automatic re-running of debate when agent output changes
- Persisting job output across server restarts
- Authentication / access control on the deploy endpoint
- Migration to FastAPI

---

## Success Criteria

1. Clicking "Deploy Fix Agent" on a pre-loaded bug spawns `claude` CLI and streams real agent output into the deploy panel
2. Clicking "Get AI Analysis" on a dynamically detected bug generates a full A/B debate via the Anthropic API and renders it in the card
3. Repeated clicks on "Get AI Analysis" return the cached debate (no duplicate API calls)
4. If `claude` is not on PATH, a clear error appears in the deploy panel
5. If `ANTHROPIC_API_KEY` is not set, a clear error appears when requesting a debate
6. Server remains responsive during a running agent (deploy runs in background thread)
