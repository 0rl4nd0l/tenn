# Cockpit Cheat Sheet

This is a practical operator guide for the Cockpit chat panel and pre-boot screen.

## Daily Use Commands

### Settings And Access

```text
/request-access web
/request-access rag
/request-access dbdiag
/web on
/web off
/rag on
/rag off
/dbdiag on
/dbdiag off
/access
/health
/prompt
/sources on
/sources off
/prefer key=value
/prefer
```

### Action Control

```text
/confirm
/cancel
/restart backend
```

### Watchlist

```text
/watch add BHP
/watch remove BHP
/watch list
/watch clear
```

### Transcript Review

```text
/review list
/review approve <source_id>
/review reject <source_id>
/review approve-all
/review expired
```

### Strategy

```text
/strategy list
/strategy list BHP
/strategy add iron ore discipline
/strategy add BHP low-cost producer
/strategy decide BHP buy strong cash generation
/strategy delete <id>
```

### Utility

```text
/run <action_id> key=value
/read <path>
/read <path> max_chars=20000
```

## Natural Language Shortcuts

Cockpit also maps some normal phrases into slash commands.

Examples:

```text
enable web access
disable web access
turn on rag
turn off rag
what access
show my watchlist
approve all transcripts
```

## Pre-Boot Settings

These are the main controls shown before launching Cockpit.

The LLM panel is read-only. By default it reflects the merged effective config from `financial-engine_v2/config/cockpit_llm.yaml`; `COCKPIT_*` LLM env vars only win when that file sets `allow_env_override: true`. Pre-boot no longer exports direct provider/model env vars on launch.

### Read-only Mode

Blocks mutating actions.

Use it when:
- you are exploring or debugging
- you do not want accidental ingest, extraction, or state changes

Avoid it when:
- you intend to run actions that mutate data or runtime state

### Enable Web Fetch

Allows web search and URL fetch workflows.

Use it when:
- you want current information
- you want to inspect URLs directly
- you are doing broader research, not just local-database work

Turn it off when:
- you want a strictly local workflow
- you are testing deterministic local-only behavior

### Enable Embedding + RAG

Enables qualitative/news retrieval context in Cockpit.

Use it when:
- you want richer local context
- you want announcement/news-backed answers

Turn it off when:
- you want a lightweight or faster test session
- you are debugging chat behavior without retrieval noise

### Verbose Logging

Raises logging verbosity and sends more detail to stderr/log output.

Use it when:
- debugging runtime issues
- tracing why a model, action, or retrieval path behaved a certain way

Turn it off for normal use.

### Profile

Current profiles:

- `Full`
  - normal operating mode
  - read-only off
  - web on
  - RAG on
  - verbose off

- `Testing`
  - safer debugging mode
  - read-only on
  - RAG off
  - verbose on
  - shorter context-gather timeout

Recommended default:
- `Full` for normal operator use
- `Testing` for debugging or UI/runtime validation

### Chat Model

Selects the primary chat/runtime model.

Recommended:
- use a strong general local model for normal chat
- use a coder model only when you actually want code-heavy help

### Extraction Model

Selects the model used for extraction/runtime-guarded extraction flows.

Recommended:
- use an instruct model
- keep it separate from the coding/chat model when possible

### Load Model Into RAM

This disables mmap.

Tradeoff:
- faster prefill after load
- slower startup / model switching
- more RAM pressure

Recommended:
- keep it on only if your machine has enough RAM and you care about steady-state speed
- turn it off if startup/switching cost or memory pressure is the bigger issue

### Enable Router Mode When Supported

This enables hot model switching for local `llama.cpp` when the runtime supports it.

Recommended:
- on for interactive Cockpit use
- off if you want the simplest single-model runtime behavior

Important:
- router mode is best for live switching
- single-model mode is simpler but requires restarts for model swaps

### Advanced Model Routing

These fields control agent-side model role preferences.

- `Orchestrator`
  - heavier model for high-level planning and synthesis

- `Sub-agent`
  - smaller/faster model for lighter delegated work

- `Router policy`
  - `local_only`: stay on local runtime only
  - `local_preferred`: prefer local, allow API fallback
  - `api_preferred`: prefer API path when available

Recommended default:
- `local_only`

## Ideal Settings

### Normal Daily Research

- Profile: `Full`
- Read-only: off
- Web: on
- RAG: on
- Verbose: off
- Router mode: on if supported
- Router policy: `local_only`

### Debugging / Safe Investigation

- Profile: `Testing`
- Read-only: on
- Web: optional
- RAG: off
- Verbose: on
- Router mode: on if you are testing model switching, otherwise optional

### Live Model Switching Session

- Profile: `Full`
- Router mode: on
- Chat model: preferred primary local model
- Extraction model: stable instruct model
- Load model into RAM: only if memory headroom is good

## Example Workflows

### 1. Normal Company Research

1. Launch with `Full`.
2. Keep web and RAG enabled.
3. Ask:
   - `tell me about CSL`
   - `show chart`
   - `what changed for BHP`

Notes:
- follow-up requests like `show chart` reuse the prior ticker context
- unrelated chat should not force a fake ticker context

### 2. Safe Runtime / Prompt Debugging

1. Launch with `Testing`.
2. Confirm read-only is on.
3. Turn verbose logging on.
4. Use:
   - `/access`
   - `/health`
   - `/prompt`
   - `/sources on`

### 3. Enable Web Temporarily

1. Start local-only if preferred.
2. When needed, run:

```text
/request-access web
/confirm
```

3. Ask for current or URL-backed information.

#### API payload examples (`/api/cockpit/chat`)

Use `web_search` (not `enable_web`) when calling the backend API directly.

Explicit web search:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/cockpit/chat \
  -H 'content-type: application/json' \
  -d '{
    "message": "search web for BHP latest announcement",
    "web_search": true,
    "stream": false
  }'
```

Ingest action preview (no overlap with web-search shortcut):

```bash
curl -sS -X POST http://127.0.0.1:8000/api/cockpit/chat \
  -H 'content-type: application/json' \
  -d '{
    "message": "ingest BHP",
    "web_search": true,
    "stream": false
  }'
```

Expected:
- first call returns a WEB-mode result with web evidence
- second call returns an `action_preview` for `single_ticker_announcement_backfill`

### 3b. Backend-Gated Access And Runtime Repair

Access toggles are backend-owned. Cockpit proposes a backend action first, then applies it after confirmation.

Typical flow:

```text
/request-access rag
/confirm
/access
```

What happens:
- Cockpit builds a `__backend_proposal__` action preview for `enable_*` or `disable_*` access scopes.
- `/confirm` applies that proposal through the backend control-plane endpoints.
- `/access` reflects the backend-written access state for `web`, `rag`, and `dbdiag`.

The same control-plane also exposes runtime remediation proposals. If extraction is unreachable, backend capabilities can surface `start_extraction_runtime`, and Cockpit can confirm that proposal instead of guessing a local recovery path.

### 4. Transcript Review

1. Check staged items:

```text
/review list
```

2. Approve or reject:

```text
/review approve <source_id>
/review reject <source_id>
```

### 5. Watchlist Maintenance

```text
/watch add BHP
/watch add CSL
/watch list
```

Natural language also works:

```text
show my watchlist
add BHP to watchlist
```

## Troubleshooting

### Cockpit Keeps Asking For A Ticker

If chat feels unnatural or tries to interpret ordinary words as tickers:

- mention the company clearly, e.g. `tell me about CSL`
- for follow-ups, use direct continuations like `show chart`, `what about earnings`, `and the outlook?`
- if context is wrong, reset by naming the intended ticker explicitly

### Router Mode Looks Wrong

Check:

```text
/access
/health
```

If preboot shows a router warning:
- refresh/reopen preboot
- verify there is a single chat controller runtime on port `8001`

### Access Toggle Does Not Stick

Check:

```text
/access
/health
```

If the backend is reachable but the toggle still looks wrong:
- confirm the session has backend API access configured
- remember `/request-access ...` only stages the proposal; the access state changes after `/confirm`
- backend capabilities and proposal apply are served from `/api/system/capabilities` and `/api/system/proposals/apply`

### No Sources Showing

Use:

```text
/sources on
```

### Need To Inspect A Local File Quickly

Use:

```text
/read path/to/file
/read path/to/file max_chars=20000
```
