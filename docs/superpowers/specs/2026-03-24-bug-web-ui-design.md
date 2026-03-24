# Bug Monitor Web UI — Design Spec

**Date:** 2026-03-24
**Status:** Approved
**File in scope:** `.claude/monitors/bug_web_ui.py`

---

## Context

`bug_web_ui.py` is a self-contained Python `http.server` dashboard that reads `.claude/monitors/alerts.log` (written by `monitor_agents.py`, which runs 5 Claude API monitoring agents in parallel threads). The file already contains:

- A `KNOWN_FIXES` dict (module-level Python dict) with 4 pre-loaded bugs (explanation, A/B agent debate, proposed diff, verdict)
- A full dark-theme HTML/JS frontend with bug cards, collapsible tabs (Explanation / Agent Debate / Proposed Fix), diff syntax highlighting, and a "Deploy Fix Agent" button
- A `GET /api/data` endpoint that merges live alerts with `KNOWN_FIXES`
- `POST /api/deploy/<fix_id>` handlers that apply **hardcoded string-replacement patches** (not real agents)

**Goal:** Replace the hardcoded deploy handlers with real `claude` CLI subprocess invocations, and add on-demand A/B debate generation via the Anthropic Messages API for dynamically detected bugs that have no pre-loaded fix.

---

## New Module-Level Globals

Add at module level (alongside `REPO_ROOT`, `LOG_FILE`, etc.):

```python
import hashlib, shutil, socketserver, threading, time
JOBS: dict[str, dict] = {}          # keyed by fix_id; stores running agent jobs
_JOBS_LOCK = threading.Lock()       # guards all reads/writes to JOBS
_DEBATES_LOCK = threading.Lock()    # guards all reads/writes to debates.json
```

`DEBATES_DB = Path(__file__).parent / "debates.json"` already exists in the current file (line 24) — no change needed.

**`_load_json_safe` helper** (already needed for `debates.json`; define once if not already present):
```python
def _load_json_safe(path: Path) -> dict | None:
    """Return parsed JSON dict from path, or None on any error (missing, invalid JSON, non-dict)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None
```

---

## Architecture

`http.server.HTTPServer` is replaced with a `ThreadingMixIn` variant for concurrent connections:

```python
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
```

Three new capabilities are added to the existing server:

---

### 1. On-Demand Debate — `POST /api/debate/<issue_id>`

For alerts without a `KNOWN_FIXES` entry, generates a live A/B agent debate using the Anthropic Messages API.

**Cache key (stable SHA-1):** The current `parse_alerts()` sets `current["id"] = str(uuid.uuid4())` at the header-match block (before issues are parsed). This is replaced by computing the hash in the issue-append block, where the issue fields are available. Concretely, the change inside `parse_alerts()` is:

```python
# Before (in the ⚠ / issue-append block, after appending to current["issues"]):
current["issues"].append({...})

# After — set id the first time an issue is appended:
issue_dict = {"type": ..., "location": ..., "detail": ...}
current["issues"].append(issue_dict)
if len(current["issues"]) == 1:   # set once, on first issue
    current["id"] = hashlib.sha1(
        f"{current['agent']}:{issue_dict['type']}:{issue_dict['location']}:{issue_dict['detail']}".encode()
    ).hexdigest()
```

Remove the `current["id"] = str(uuid.uuid4())` assignment from the header-match block. Alerts that have no issues retain no meaningful id and are filtered out by `get_open_issues()`, so no id is needed for them.

Because `get_open_issues()` already splits alerts to one issue per item, each returned item has exactly one issue and a unique stable SHA-1. This key is stable across server restarts and page reloads.

**Input:** `issue_id` URL parameter (must match `^[a-f0-9]{40}$` — 400 otherwise), request body JSON:
```json
{"agent": "BUGS", "severity": "critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
```
Read body safely: `content_length = int(self.headers.get("Content-Length") or 0)` (wrap in `try/except ValueError` → return 400 if non-numeric), then `body = self.rfile.read(min(content_length, 8192))`.

**Output (success):**
```json
{
  "agent_a": {"name": "Agent A — Minimal Fix", "approach": "...", "diff": "..."},
  "agent_b": {"name": "Agent B — Comprehensive Fix", "approach": "...", "diff": "..."},
  "verdict": "...",
  "winning_agent": "a" | "b" | "both" | null
}
```

**Debate system prompt:**
```
You are a code-fix debate moderator. You will be given a detected code issue.
Propose TWO competing fixes: Agent A (minimal — smallest safe change) and Agent B
(comprehensive — cleaner abstraction). Then give a verdict on which is better.

Respond with ONLY a valid JSON object matching this exact schema:
{
  "agent_a": {"name": "Agent A — Minimal Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},
  "agent_b": {"name": "Agent B — Comprehensive Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},
  "verdict": "<explanation of which is better and why>",
  "winning_agent": "a" | "b" | "both" | null
}
No markdown fences. No preamble. JSON only.
```

**Debate user message:**
```
Agent: {agent}
Severity: {severity}
Issue type: {issue_type}
Location: {location}
Detail: {detail}

Propose two fixes and give a verdict.
```

**Flow:**
1. Validate `issue_id` regex → 400 if invalid
2. Parse + validate request body → 400 if malformed or oversized
3. Acquire `_DEBATES_LOCK`, load `debates.json`, check for existing entry → release lock, return if found
4. Call Anthropic API (model: `claude-sonnet-4-6`, max_tokens: 2048, system + user messages above)
5. Strip markdown fences if present (`if "```" in raw: raw = raw.split("```")[1]; if raw.startswith("json"): raw = raw[4:]`), then `json.loads()`
6. Acquire `_DEBATES_LOCK`, load `debates.json` (or `{}`), write entry keyed by `issue_id`, save → release lock
7. Return debate object

**Error cases:**
- `ANTHROPIC_API_KEY` not set → `{"ok": false, "message": "ANTHROPIC_API_KEY not set"}`
- JSON parse failure → `{"ok": false, "message": "Model response was not valid JSON: <raw[:300]>"}`
- Network/API error → `{"ok": false, "message": "<exception str>"}`

---

### 2. Claude Agent Deploy — `POST /api/deploy/<fix_id>`

Replaces all hardcoded `_fix_*` methods with a single subprocess-based dispatcher.

**`fix_id` validation:** Must match `^[a-z0-9][a-z0-9\-]{0,79}$` (slug-style KNOWN_FIXES keys) OR `^[a-f0-9]{40}$` (SHA-1 for dynamic debates). Any other shape → 400.

**Task string construction:**

For a `KNOWN_FIXES` entry where `winning_agent` is not None:
```
Fix the following confirmed bug in {fix["file"]}:

Issue: {fix["title"]}
Winning approach: {agent["name"]} — {agent["approach"]}

Proposed diff for reference:
{agent["diff"]}

Steps:
1. Read {fix["file"]} to confirm the exact current code
2. Apply the fix described above
3. Run: ruff check {fix["file"]}
4. If ruff passes, create a git commit: fix(<subsystem>): <brief title>
```
where `agent` = `fix["agent_b"]` if `winning_agent == "b"`, else `fix["agent_a"]` (covers `"a"` and `"both"`; Agent A is preferred when both are recommended).

For a `KNOWN_FIXES` entry where `winning_agent` is `None` (investigation required):
```
Investigate and fix the following issue in {fix["file"]}:

Issue: {fix["title"]}
Description: {fix["explanation"]}

Two approaches have been proposed:
- Agent A: {fix["agent_a"]["approach"]}
- Agent B: {fix["agent_b"]["approach"]}

Steps:
1. Read {fix["file"]} and all relevant files it imports
2. Determine which approach is correct given the current code state
3. Apply the better fix
4. Run ruff check and pytest for the affected module
5. Create a git commit: fix(<subsystem>): <brief title>
```

For a dynamic debate entry (from `debates.json`):
```
Fix the following detected code issue:

Location: {location}
Issue type: {issue_type}
Detail: {detail}
Winning approach: {winning_agent_name} — {winning_agent_approach}

Steps:
1. Read the file at {location.split(':')[0]} to confirm the exact current code
2. Apply the fix described above
3. Run ruff/pytest as appropriate
4. Create a git commit: fix(<subsystem>): <brief description>
```
If `winning_agent` is None for a dynamic debate, use this template:
```
Fix the following detected code issue (approach undecided — investigate and choose):

Location: {location}
Issue type: {issue_type}
Detail: {detail}

Two approaches proposed:
- Agent A: {agent_a_approach}
- Agent B: {agent_b_approach}

Steps:
1. Read the file at {location_file} to confirm the exact current code
2. Choose and apply the better fix
3. Run ruff/pytest as appropriate
4. Create a git commit: fix(<subsystem>): <brief description>
```
where `location_file = location.split(':')[0]`.

**Subprocess command (list form, no shell=True):**
```python
cmd = [
    "claude",
    "--allowedTools", "Edit,Read,Bash,Glob,Grep",
    "--print",
    "-p", task_string,  # task_string is passed as a list element, no quoting needed
]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
```
Using list form with `shell=False` (default) prevents shell injection. `shlex.quote()` is NOT used — it is for shell string interpolation only and would corrupt the argument when passed as a list element.

**Flow:**
1. Validate `fix_id` format → 400 if invalid
2. `shutil.which("claude")` → 503 with message `"claude CLI not found — ensure it is on PATH"` if None
3. Look up task string from `KNOWN_FIXES` or `debates.json` (under `_DEBATES_LOCK`) → 404 if neither found
4. Construct task string per templates above
5. Acquire `_JOBS_LOCK`, register `JOBS[fix_id] = {"status": "running", "output": [], "exit_code": None}`, release
6. Spawn `threading.Thread(target=_run_agent_job, args=(fix_id, cmd), daemon=True).start()`
7. Return immediately: `{"ok": true, "status": "running"}`

**Worker thread `_run_agent_job(fix_id, cmd)`:**
```python
def _run_agent_job(fix_id, cmd):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 300
    for line in proc.stdout:
        with _JOBS_LOCK:
            JOBS[fix_id]["output"].append(line.rstrip())
        if time.time() > deadline:
            proc.kill()
            proc.wait()
            with _JOBS_LOCK:
                JOBS[fix_id]["status"] = "error"
                JOBS[fix_id]["output"].append("[timeout after 300s]")
                JOBS[fix_id]["exit_code"] = -1
            return
    proc.wait()
    with _JOBS_LOCK:
        JOBS[fix_id]["status"] = "done" if proc.returncode == 0 else "error"
        JOBS[fix_id]["exit_code"] = proc.returncode
```

---

### 3. Job Status Poll — `GET /api/job/<fix_id>`

Added to `do_GET` routing alongside `/api/data`.

**Output:**
```json
{"status": "running" | "done" | "error", "output": ["line1", "line2", ...], "exit_code": 0 | 1 | null}
```

`output` is a list of strings (one per stdout line). Frontend joins with `\n` for display and compares `output.length` between polls to append only new lines.

Frontend polls every 1500ms until `status != "running"`.

---

### 4. Updated `/api/data` — Merge Cached Debates

`do_GET` for `/api/data` already merges `KNOWN_FIXES`. It is updated to also merge `debates.json`: for any alert whose `id` (stable SHA-1) has an entry in `debates.json`, that entry is included as `known_fix` in the response (with `fix_id` set to the SHA-1). This ensures that after a page reload, previously generated debates are immediately visible without requiring another "Get AI Analysis" click.

```python
# Load debates once per request (under _DEBATES_LOCK)
with _DEBATES_LOCK:
    cached_debates = _load_json_safe(DEBATES_DB) or {}

for item in open_issues:
    fix_id, fix = match_known_fix(item)
    if fix is None and item["id"] in cached_debates:
        fix_id = item["id"]
        fix = cached_debates[item["id"]]
    result.append({**item, "fix_id": fix_id, "known_fix": fix})
```

---

## Frontend Changes

### Stable `issue_id` computation (server-side change)

`parse_alerts()` replaces `str(uuid.uuid4())` with the stable SHA-1 formula. The `current["id"]` is set once when the first issue is added. No frontend changes needed for this — it is transparent.

### `loadDebate(issueId, itemData)`
- Called when user clicks "Get AI Analysis"; `itemData` is the full item object from `allData` (shape: `{id, agent, severity, issues, fix_id, known_fix, ...}`)
- Replaces card body with spinner: `"Generating agent debate…"`
- POSTs to `/api/debate/<issueId>` with `JSON.stringify({agent: itemData.agent, severity: itemData.severity, issues: itemData.issues})` as body (only the three fields the server needs)
- On success: re-renders card body using `makeBugCard` template logic (full tabs: Explanation / Agent Debate / Proposed Fix)
- On error: shows `"Debate generation failed: <message>"` with a "Retry" button

### Updated `deployFix(fixId, btn)`
- POSTs to `/api/deploy/<fixId>`
- On `{ok: true}`: enters polling loop — GET `/api/job/<fixId>` every 1500ms
- Each poll: compares `data.output.length` to `lastLen`, appends new lines to `#output-<fixId>` (no full re-render), updates `lastLen`
- Stops polling when `data.status != "running"`
- On `done`: button → "✓ Fix Applied", green, disabled
- On `error`: button → "↺ Retry", re-enabled; output panel shows full log

### "Get AI Analysis" replaces "Investigate & Fix"

The existing "Investigate & Fix" button (line 464 of current code) that calls `deployFix` directly is **replaced** by a "Get AI Analysis" button that calls `loadDebate` first. After the debate loads (success path), the card re-renders with the full tab bar including a "Deploy Fix Agent" button. This enforces the sequence: generate debate → review → deploy.

---

## Security

**Input validation:**
- `fix_id` in URL validated against strict regex before any lookup or subprocess spawn
- `issue_id` in URL validated against `^[a-f0-9]{40}$`
- Request bodies: `content_length = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(min(content_length, 8192))`

**Subprocess safety:**
- `claude` binary path resolved via `shutil.which("claude")` — not a shell glob
- Task string passed as a list element to `Popen` with `shell=False` (default) — no shell injection possible regardless of task string content
- `shlex.quote()` is NOT used (it is for shell string interpolation only; using it with list-form Popen would corrupt the argument)

**Scope note:** Server binds to `0.0.0.0` (existing behaviour). The deploy endpoint has no authentication. This is acceptable for a local developer tool on a trusted network.

---

## Data Files

| File | Purpose |
|------|---------|
| `.claude/monitors/alerts.log` | Written by `monitor_agents.py` — read-only input |
| `.claude/monitors/debates.json` | Written by on-demand debate endpoint — keyed by stable SHA-1; guarded by `_DEBATES_LOCK` |

`JOBS` dict is in-memory only (lost on server restart — acceptable since jobs complete in under 5 minutes).

---

## Routing Summary (do_GET / do_POST)

| Method | Path | Handler |
|--------|------|---------|
| GET | `/` | Serve HTML |
| GET | `/api/data` | Return merged alerts + KNOWN_FIXES + cached debates |
| GET | `/api/job/<fix_id>` | Return job status + output list |
| POST | `/api/debate/<issue_id>` | Generate/return A/B debate |
| POST | `/api/deploy/<fix_id>` | Spawn claude agent, return `{ok, status}` |

---

## Constraints

- **Scope:** Only `bug_web_ui.py` is modified. No changes to `monitor_agents.py`, `alerts.log` format, or the `KNOWN_FIXES` data.
- No new Python files created (except `debates.json` at runtime).
- `http.server.HTTPServer` is retained, wrapped with `ThreadingMixIn`.
- The `claude` CLI must be on PATH for deploy to work (soft dependency — degrades gracefully).
- `ANTHROPIC_API_KEY` must be set for on-demand debate (same as `monitor_agents.py`).

---

## Out of Scope

- SSE streaming (polling is sufficient)
- Automatic debate re-generation when alert changes
- Authentication on the deploy endpoint
- FastAPI migration

---

## Success Criteria

1. Clicking "Deploy Fix Agent" on a pre-loaded bug spawns `claude` CLI and streams real agent output into the deploy panel
2. Clicking "Get AI Analysis" on a dynamically detected bug generates a full A/B debate and renders it in the card
3. Repeated "Get AI Analysis" clicks on the same alert return the cached debate (no duplicate API calls)
4. After a page reload, previously generated debates are immediately visible (via `/api/data` merge)
5. If `claude` is not on PATH, a clear error appears in the deploy panel immediately
6. If `ANTHROPIC_API_KEY` is not set, a clear error appears when requesting a debate
7. Server remains responsive during a running agent (ThreadingMixIn + background thread)
8. The same alert produces the same `issue_id` across page reloads and server restarts (stable SHA-1 key)
