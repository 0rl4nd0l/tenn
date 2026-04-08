# Cockpit Web UI Modernization Plan

> **Purpose:** This document is a self-contained implementation plan for converting the cockpit from a Textual TUI to a proper web UI. It contains all context needed to execute in a fresh session without prior conversation history.

---

## Background & Motivation

The cockpit is a financial analysis workstation — chat interface, data operations, verification, news search, watchlist/strategy management. It currently runs as a **Python Textual TUI** served to the browser via WebSocket (`textual serve`). The browser acts as a thin terminal emulator rendering 16-bit color frames.

**Why convert:** The TUI-in-browser approach limits UX — single-line input, no clickable elements, no inline charts, no proper layout, keyboard-only navigation. A proper web UI unlocks multi-line input, inline Plotly charts, responsive layout, clickable interactions, and a more polished experience. The app remains **local-only** (localhost).

---

## Current Architecture (READ THIS FIRST)

### Files Being Replaced

| File | Lines | Role |
|------|-------|------|
| `financial-engine_v2/cockpit/ui/app.py` | 2,177 | Main Textual App — chat loop, action execution, all screen management |
| `financial-engine_v2/cockpit/ui/screens.py` | 665 | 7 screen definitions (Chat, Ops, Updater, Verification, History, Settings, News) |
| `financial-engine_v2/cockpit/ui/preboot.py` | 833 | Pre-boot health check screen, service probing, launch configuration |
| `financial-engine_v2/cockpit/ui/web.py` | 157 | CockpitWebApp wrapper for web-specific initialization |
| `financial-engine_v2/cockpit/ui/help_modal.py` | 72 | Help modal with keybinding display |
| **Total** | **3,904** | |

### Files That Stay Unchanged

These are the **core logic** files that the new frontend will consume via HTTP:

| File | Role |
|------|------|
| `cockpit/core/tools.py` | ToolRouter — orchestrates all tool calls (DB, web, file, RAG, search) |
| `cockpit/core/tool_executor.py` | ToolExecutor — executes individual tool definitions |
| `cockpit/core/chat.py` | ChatController — builds LLM responses, classifies requests, streams chunks |
| `cockpit/core/config.py` | Config loading (cockpit.yaml + cockpit_llm.yaml + env vars) |
| `cockpit/core/actions.py` | ActionRegistry — action preview/execution/confirmation |
| `cockpit/core/state_store.py` | StateStore — SQLite persistence (chat history, preferences, jobs) |
| `cockpit/core/research/deep_research.py` | DeepResearchRunner — autonomous multi-step research |
| `cockpit/integrations/backend_api.py` | BackendApiClient — HTTP client to FastAPI backend on :8000 |
| `cockpit/integrations/llamacpp_client.py` | LlamaCppClient — chat inference via llama.cpp |
| All `backend/` files | FastAPI backend — unchanged, gains new cockpit API routes |

### Entrypoints

| Current | New |
|---------|-----|
| `scripts/cockpit_web.py` → Textual WebSocket serve | `scripts/cockpit_web.py` → FastAPI serves HTML + API |
| `scripts/cockpit_tui.py` → direct terminal TUI | Stays unchanged (TUI mode preserved for terminal users) |
| `scripts/cockpit` — launcher script | Updated to launch new web mode |

### Service Initialization Flow (IMPORTANT)

Currently, `CockpitWebApp` initializes all services **in-process** inside the Textual app:

```
CockpitWebApp.__init__()
  → PreBootScreen (health checks)
  → _on_preboot_launch()
    → _init_services() in background thread:
        → BackendApiClient
        → LlamaCppClient
        → ToolRouter (with backend, db_reader, file_indexer, web_fetcher, brave, hn)
        → ChatController (with tool_router)
        → StateStore
        → ActionRegistry
```

In the new architecture, this initialization moves to a **CockpitService** singleton that lives inside the FastAPI app lifecycle (startup event). The frontend consumes it via REST/SSE.

### Screens & Their Features

**ChatScreen** (primary — 80% of usage):
- Conversational Q&A with financial data context
- Streaming responses from local llama.cpp or Anthropic Claude
- Action detection → preview → user confirmation → execution
- 35+ slash commands (`/watch`, `/strategy`, `/confirm`, `/cancel`, `/read`, `/run`, `/web`, `/rag`, `/health`, `/review`, etc.)
- Source attribution footer (RAG results)
- Routing metadata (model, latency, cost)
- Input history navigation (Ctrl+Up/Down)

**OperationsScreen:**
- Feature toggles: web search on/off, RAG on/off, DB diagnostics on/off
- Action selector dropdown + args input + Execute/Preview buttons
- Service status display (backend, llama.cpp, Ollama, Qdrant, Redis)
- Session API cost tracker

**UpdaterScreen:**
- Fetch/refresh ticker financial data
- Multi-year backfill (default 5 years)
- Toggle document processing
- Show latest financial row + audit confidence

**VerificationScreen:**
- Run data integrity checks (broad or by ticker)
- Results display with pass/fail
- Export as JSON + HTML dashboard
- Plotly candlestick/snapshot chart generation

**HistoryScreen:**
- Past jobs table (sortable)
- Job detail view
- Re-run button

**SettingsScreen:**
- Read-only config display (grouped)
- Capabilities display
- Environment info

**NewsSearchScreen:**
- Semantic search over Qdrant or SQLite fallback
- Filters: ticker, date range, lookback (24h/7d/30d/all)
- Results with source, date, relevance score

### Backend API Endpoints (Already Existing)

These endpoints on the FastAPI backend (:8000) are already implemented:

```
GET  /api/health              — service availability
GET  /api/capabilities        — feature flags
POST /api/chat                — chat inference (HybridRouter)
GET  /api/ticker_context      — financial data + documents
POST /api/proposals/{id}      — apply access control changes
GET  /api/transcripts         — pending commentary chunks
POST /api/transcripts/{id}/approve
POST /api/transcripts/{id}/reject
```

### LLM Configuration

- Chat inference: llama.cpp at `LLAMACPP_URL` (default :8001)
- Embeddings: Ollama at `OLLAMA_URL` (default :11434)
- Anthropic (optional): requires `ANTHROPIC_API_KEY`
- Routing policy: `hybrid_router_policy` in `config/cockpit_llm.yaml`
- Models: qwen2.5-coder-14b (chat), nomic-embed-text (embeddings)

---

## Architecture Decision: FastAPI + Jinja2 + Vanilla JS

**No React/Vue/Node.js.** This is a single-user local tool.

| Factor | Decision |
|--------|----------|
| Build step | None — no npm, no webpack, no bundler |
| Templates | Jinja2 (already a FastAPI dependency) |
| Styling | Vanilla CSS with custom properties for theming |
| JavaScript | Vanilla JS (ES modules) |
| Streaming | Server-Sent Events (SSE) via `sse-starlette` |
| Markdown | `marked.js` vendored as static file (~40KB) |
| Code highlighting | `highlight.js` vendored (~30KB) |
| Charts | `plotly.js` vendored (already used in project) |
| HTTP client | Browser `fetch()` API |

**Why this stack:** Keeps the project Python-only. No Node.js toolchain. No build step. Edit a file, refresh the browser. The API layer built here also serves as foundation if the user later wants a React frontend.

---

## Implementation Phases

### Phase 0: API Surface Audit & Gap Analysis
**Complexity: LOW**

Catalog what the current FastAPI backend exposes vs. what the Textual UI calls directly in Python. Document the gap.

**Known gaps — new endpoints needed:**

| Feature | Current (in-process) | New endpoint |
|---------|---------------------|-------------|
| Chat + streaming | `chat_controller.build_chat_response()` | `POST /api/cockpit/chat` → SSE |
| Slash commands | Parsed in `app.py` | `POST /api/cockpit/command` |
| Action preview | `ActionRegistry` in-process | `POST /api/cockpit/actions/{id}/preview` |
| Action confirm/execute | `ActionRegistry` + `JobRunner` | `POST /api/cockpit/actions/{id}/execute` → SSE |
| Job status | `JobRunner` in-process | `GET /api/cockpit/jobs/{id}/status` |
| Watchlist CRUD | `state_store` direct | `GET/POST/DELETE /api/cockpit/watchlist` |
| Watchlist scan | `state_store` + tools | `POST /api/cockpit/watchlist/scan` |
| Strategy CRUD | `state_store` direct | `GET/POST/DELETE /api/cockpit/strategy` |
| Strategy decide | `state_store` direct | `POST /api/cockpit/strategy/decide` |
| Preferences | `state_store` direct | `GET/PUT /api/cockpit/preferences` |
| Chat history | `state_store` direct | `GET /api/cockpit/history` |
| Aggregated health | In-process probes | `GET /api/cockpit/health` |
| Config + capabilities | In-process config | `GET /api/cockpit/config` |
| File read (`/read`) | `file_indexer` in-process | `POST /api/cockpit/files/read` |
| Review commands | `state_store` + backend | `GET/POST /api/cockpit/reviews` |

**Deliverable:** Gap analysis document listing every new endpoint with request/response shapes.

---

### Phase 1: Cockpit API Layer
**Complexity: MEDIUM | ~600 lines**

Build the missing REST endpoints as a new FastAPI router.

**Key tasks:**
1. Create `financial-engine_v2/backend/app/routes/cockpit_api.py` — new router
2. Create `financial-engine_v2/cockpit/core/cockpit_service.py` — shared service singleton:
   - Holds: ChatController, ToolRouter, StateStore, ActionRegistry, JobRunner
   - Initialized lazily on first request (not at import time)
   - Same initialization logic as current `_init_services()` in app.py
3. Implement all endpoints from the gap analysis above
4. SSE streaming for chat (`sse-starlette` or raw `StreamingResponse`):
   - Chat chunks streamed as `data: {"type": "chunk", "text": "..."}\n\n`
   - Final message: `data: {"type": "done", "sources": [...], "metadata": {...}}\n\n`
   - Action preview: `data: {"type": "action_preview", "action": {...}}\n\n`
5. SSE streaming for job output (long-running actions like extraction/backfill)
6. Unit tests for each endpoint
7. Register router in `backend/app/main.py`

**Critical detail — chat SSE response shape:**
```json
// Streamed chunks
{"type": "chunk", "text": "The revenue for BHP..."}
{"type": "chunk", "text": " increased by 12%..."}

// Tool traces (if debug enabled)
{"type": "tool_trace", "tool": "ticker_context", "duration_ms": 450}

// Sources (if RAG)
{"type": "sources", "items": [{"title": "...", "url": "...", "score": 0.87}]}

// Action preview (if detected)
{"type": "action_preview", "id": "show_candlestick", "args": {"ticker": "BHP"}, "description": "Generate candlestick chart for BHP"}

// Final metadata
{"type": "done", "model": "qwen2.5-coder-14b", "latency_ms": 2340, "cost_usd": 0.0, "source": "local"}
```

---

### Phase 2: Frontend Foundation
**Complexity: MEDIUM | ~800 lines**

**Directory structure:**
```
financial-engine_v2/cockpit/frontend/
├── static/
│   ├── css/
│   │   ├── base.css          # Reset, CSS variables, typography
│   │   ├── layout.css        # Sidebar, main content, responsive grid
│   │   ├── chat.css          # Chat-specific styles
│   │   └── components.css    # Buttons, cards, modals, tables, toggles
│   ├── js/
│   │   ├── app.js            # Main init, page routing, global state
│   │   ├── api.js            # Fetch wrapper, SSE helper, error handling
│   │   ├── chat.js           # Chat UI: message list, input, streaming, commands
│   │   ├── actions.js        # Action preview/confirm modal
│   │   ├── ops.js            # Operations page logic
│   │   ├── updater.js        # Updater page logic
│   │   ├── verification.js   # Verification page logic
│   │   ├── history.js        # History page logic
│   │   ├── news.js           # News search logic
│   │   └── components.js     # Reusable: modals, toasts, tables, badges
│   └── vendor/
│       ├── marked.min.js     # Markdown rendering (~40KB)
│       ├── highlight.min.js  # Syntax highlighting (~30KB)
│       └── plotly.min.js     # Charts (~3.5MB, already used in project)
├── templates/
│   ├── base.html             # Shell: sidebar, header, main content area, status bar
│   ├── chat.html             # Chat page
│   ├── ops.html              # Operations page
│   ├── updater.html          # Updater page
│   ├── verification.html     # Verification page
│   ├── history.html          # History page
│   ├── settings.html         # Settings page
│   ├── news.html             # News search page
│   ├── boot.html             # Pre-boot health check page
│   └── partials/
│       ├── sidebar.html      # Navigation sidebar
│       ├── status_bar.html   # Bottom bar: model, services, cost
│       ├── health_badge.html # Service health indicator
│       └── action_modal.html # Action preview/confirm dialog
```

**Key tasks:**
1. FastAPI static file serving: `app.mount("/static", StaticFiles(...))`
2. Jinja2 template rendering for each page
3. `base.html` layout:
   - Left sidebar: nav links with icons for each screen
   - Top header: cockpit name, current ticker context, connection status
   - Main content area: page-specific content
   - Bottom status bar: active model, connected services, session cost
4. Dark theme (matching terminal aesthetic):
   - Background: `#1a1a2e` / `#16213e`
   - Text: `#e0e0e0`
   - Accent: `#0f3460` / `#533483`
   - Success/error/warning colors
   - Monospace font for data, sans-serif for UI
5. `api.js` — fetch wrapper:
   - `api.get(path)`, `api.post(path, body)`, `api.delete(path)`
   - `api.stream(path, body, onChunk)` — SSE consumer
   - Automatic error toast on 4xx/5xx
6. Page routing: SPA-style with `pushState` or simple full-page navigation (Jinja2 renders each page)
7. Vendor JS libraries as static files (no CDN — local-only app)

**Design tokens (CSS variables):**
```css
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-surface: #0f3460;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --accent: #533483;
    --success: #2ecc71;
    --error: #e74c3c;
    --warning: #f39c12;
    --font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --radius: 6px;
    --sidebar-width: 220px;
}
```

---

### Phase 3: Chat Interface (CRITICAL PATH)
**Complexity: HIGH | ~1,000 lines**

This is 80% of cockpit usage. Build and validate this before other screens.

**Chat message list:**
- Scrollable container, auto-scroll on new messages
- User messages: right-aligned, accent background
- Assistant messages: left-aligned, rendered markdown (via marked.js)
- Code blocks with syntax highlighting (highlight.js) and copy button
- Collapsible "Sources" section after RAG-augmented responses
- Subtle metadata footer: model, latency, cost

**Input area:**
- Multi-line `<textarea>` (major UX upgrade over TUI single-line)
- Send button + Enter to send (Shift+Enter for newline)
- Slash command hint (show available commands on `/` input)
- Input history: up/down arrow recalls previous messages (stored in sessionStorage)
- Character count or token estimate (optional)

**SSE streaming implementation:**
```javascript
async function sendChat(message) {
    const source = api.stream('/api/cockpit/chat', { message });
    let responseDiv = createAssistantMessage();

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.type) {
            case 'chunk':
                appendChunk(responseDiv, data.text);
                break;
            case 'sources':
                renderSources(responseDiv, data.items);
                break;
            case 'action_preview':
                showActionPreview(data);
                break;
            case 'tool_trace':
                appendToolTrace(responseDiv, data);
                break;
            case 'done':
                finalizeMessage(responseDiv, data);
                break;
        }
    };
}
```

**Action preview/confirm flow:**
- When SSE sends `action_preview`, show a card below chat:
  - Action name, description, args
  - "Confirm" (green) + "Cancel" (red) buttons
  - On confirm → POST to `/api/cockpit/actions/{id}/execute` → stream job output
- Replaces the TUI's `/confirm` / `/cancel` slash commands (still supported as aliases)

**Slash command handling:**
- If message starts with `/`, send to `/api/cockpit/command` instead of `/api/cockpit/chat`
- Response rendered as system message (different styling)

**Inline charts:**
- When action result includes Plotly data (candlestick, snapshot), render inline using Plotly.js
- No need to open external HTML file

---

### Phase 4: Operations & Control Screens
**Complexity: MEDIUM | ~1,200 lines**

Port the remaining 6 screens. Each is simpler than chat.

**4a. Operations Screen (`ops.html` + `ops.js`):**
- Toggle switches for: web search, RAG, DB diagnostics
  - Each toggle → `PUT /api/cockpit/preferences` + visual feedback
- Service health cards:
  - Backend API, llama.cpp, Ollama, Qdrant, Redis
  - Each shows: status (green/yellow/red), endpoint, response time
  - Auto-refresh every 30s
- Action executor:
  - Dropdown of available actions (from `/api/cockpit/actions`)
  - Args text input
  - "Preview" button → shows what will happen
  - "Execute" button → streams job output in a log panel
- Session cost tracker (cumulative API cost this session)

**4b. Updater Screen (`updater.html` + `updater.js`):**
- Ticker input (text field + "Fetch" button)
- Year range selector (default: 5 years)
- Checkbox: process documents
- Results panel: latest financial data as table
- Audit section: confidence scores display

**4c. Verification Screen (`verification.html` + `verification.js`):**
- "Run Verification" button (broad) + ticker-specific input
- Results table: metric, expected, actual, pass/fail badge
- Export buttons: JSON download, HTML dashboard download
- Inline Plotly chart area (candlestick, snapshot rendered in-page)

**4d. History Screen (`history.html` + `history.js`):**
- Sortable/filterable table of past jobs
- Columns: job_id, action, args, status, started_at, duration
- Click row → expand to show output log
- "Re-run" button per job

**4e. Settings Screen (`settings.html`):**
- Read-only grouped display:
  - LLM config (model, endpoint, routing policy)
  - Backend config (URL, profile)
  - Feature flags (web, RAG, extraction)
  - Environment (Python version, git branch, data_root)
- Capabilities display (from `/api/capabilities`)

**4f. News Search Screen (`news.html` + `news.js`):**
- Search input + ticker filter + date range + lookback dropdown
- Results table: headline, source, date, relevance score
- Click to expand full article text
- Indicator: "Qdrant" vs "SQLite fallback"

---

### Phase 5: Pre-boot / Health Check Flow
**Complexity: LOW | ~200 lines**

**Tasks:**
1. `boot.html` — landing page shown on first load
2. Polls `/api/cockpit/health` every 2 seconds
3. Displays service checklist:
   - [x] Backend API (green checkmark when reachable)
   - [x] llama.cpp (green when model loaded)
   - [x] Ollama embeddings (green when reachable)
   - [ ] Qdrant (yellow = optional, red = expected but down)
   - [ ] Redis (yellow = optional)
4. Progress indicator (spinner or progress bar)
5. "Launch Anyway" button — skips optional services
6. Profile selector dropdown (isolated / full)
7. On all-green (or user click): redirect to `/chat`

---

### Phase 6: Polish & Feature Parity Verification
**Complexity: LOW | ~300 lines**

1. **Keyboard shortcuts** — map where sensible:
   - `Ctrl+Enter` → send message
   - `Ctrl+K` → focus search/command
   - `Ctrl+1..7` → switch screens
   - `Escape` → close modal
2. **Toast notifications** — job complete, errors, action results
3. **Loading states** — skeleton screens, spinners for API calls
4. **Error states** — connection lost banner, retry button
5. **Export** — download markdown/JSON reports (from existing export logic)
6. **Help page** — port cockpit-cheat-sheet.md content
7. **Feature parity audit** — test every slash command, every action against TUI
8. **Launcher updates:**
   - Update `scripts/cockpit` to serve new web UI
   - Update `scripts/cockpit_web.py` as new entrypoint
   - Preserve `scripts/cockpit_tui.py` for terminal mode

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Chat SSE streaming reliability | HIGH | Implement reconnection logic; heartbeat keepalive; test with slow/fast models |
| CockpitService initialization lifecycle | MEDIUM | Lazy init on first request; health endpoint works before full init; graceful degradation |
| Slash command parity (35+ commands) | MEDIUM | Build command registry mirroring Textual impl; test each individually |
| Job output streaming for long tasks | MEDIUM | SSE with keepalive for extraction/backfill (can run 5+ min); timeout handling |
| Plotly.js bundle size (3.5MB) | LOW | Already used; load async; consider plotly-basic.min.js (~1MB) for subset |
| Browser compatibility | LOW | Local-only; user controls their browser; target Chrome/Firefox modern |

---

## Dependencies to Install

| Package | Purpose | Install |
|---------|---------|---------|
| `sse-starlette` | SSE support for FastAPI | `pip install sse-starlette` |
| `jinja2` | Template rendering | Already installed (FastAPI dep) |
| `marked.min.js` | Markdown → HTML | Vendor as static file |
| `highlight.min.js` | Code syntax highlighting | Vendor as static file |
| `plotly.min.js` | Charts | Vendor as static file (already used) |

**No Node.js. No npm. No build step.**

---

## Execution Order

```
Phase 0 (audit) → Phase 1 (API) → Phase 2 (foundation) → Phase 3 (chat) → quick Phase 6 polish
    → Ship as MVP (chat-only web UI)
        → Phase 4 (remaining screens) → Phase 5 (boot) → final Phase 6 polish
```

**Phase 3 (Chat) is the critical path.** It's 80% of usage. Get it working, validate it, then port remaining screens.

---

## Contract Compliance Notes

Per `docs/architecture/SYSTEM_CONTRACT.md`:
- This change touches **Layer 5 (Presentation)** only — no pipeline, extraction, or data integrity changes
- Backend API endpoints are additive (new cockpit router), not modifications to existing routes
- No embedding, RAG, or extraction logic changes
- No DB schema changes (uses existing state.db)
- CockpitService wraps existing classes — no new data paths

---

## Reference: Current Slash Commands (Full List)

These must all work in the new web UI:

```
# Watchlist
/watch add <TICKER>
/watch list
/watch remove <TICKER>
/watch clear
/watch scan [TICKER]

# Strategy
/strategy list [TICKER]
/strategy add [TICKER] <criterion>
/strategy decide <TICKER> <buy|watchlist|avoid>
/strategy delete <id>

# Control
/confirm
/cancel
/read <path> [max_chars=N]
/run <action_id> [args]

# Access
/request-access <web|rag|dbdiag>
/web on|off
/rag on|off
/dbdiag on|off
/health
/access
/reconnect

# Preferences
/prefer <key>=<value>
/sources on|off

# Review (commentary ingestion)
/review list
/review approve <source_id>
/review reject <source_id>
/review approve-all

# Debug
/prompt
/restart backend
```

## Reference: Current Actions (ActionRegistry)

~40 registered actions including:
- `daily_news_ingest`
- `daily_announcement_ingest`
- `historical_news_ingest`
- `single_ticker_announcement_backfill`
- `universe_announcement_enrichment_backfill`
- `metric_extraction`
- `rebuild_ticker_financials`
- `audit_ticker_financials`
- `show_candlestick`
- And more (full list from `cockpit/core/actions.py`)
