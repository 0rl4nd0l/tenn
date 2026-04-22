# Screen Catalog

Every screen in the cockpit-ui, documented with layout structure, interaction patterns, and implementation examples.

---

## Navigation Map

```
/ (Chat)  ─────────── Primary AI interaction
/operations ────────── Execute and monitor system actions
/updater ──────────── Backfill ticker financial data
/verification ─────── Document extraction quality review
/history ──────────── Past job execution records
/settings ─────────── Configuration display
/news ─────────────── Financial news search
/intel-ops ────────── Pipeline health monitoring (Intel Pulse)
/holdings ─────────── Portfolio holdings workspace
/boot ─────────────── System health onboarding
```

All screens are accessible via sidebar navigation with keyboard shortcuts (1–9, 0, W, M, N, B).

---

## 1. Chat Screen (`/`)

**Component**: `components/cockpit/chat/chat-screen.tsx`
**Role**: Primary interactive AI interface for financial analysis

### Layout

```
┌─────────────────────────────────┐
│  terminal-container (full-h)    │
│  ┌───────────────────────────┐  │
│  │  ScrollArea (messages)    │  │
│  │  ┌─────────────────────┐  │  │
│  │  │ TerminalMessage     │  │  │
│  │  │ TerminalMessage     │  │  │
│  │  │ ... (streaming)     │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  TerminalInput            │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### Key Patterns

- **Streaming indicator**: Blinking `terminal-cursor` during response generation
- **Expandable sections** in messages:
  - Sources (RAG hits with relevance scores)
  - Thinking traces (model reasoning steps)
  - Tool traces (API calls made)
  - Charts (auto-opens for financial visualizations)
- **Slash commands**: `/advisor`, `/cloud`, `/local`, `/ops` prefixes
- **Feedback capture**: Good/poor rating per message with preset notes
- **Copy to clipboard**: Prompt and response content

### Terminal Message Structure

```
┌──────────────────────────────────┐
│ [timestamp] model (latency)  ← metadata line (font-mono, text-muted-foreground)
│                                  │
│ Response content...              ← terminal-text or font-sans
│                                  │
│ ▸ Sources (3)           ← collapsible, shows relevance scores
│ ▸ Thinking (5 steps)    ← collapsible
│ ▸ Tools                 ← collapsible
│ [Chart]                 ← if applicable
│                                  │
│ 👍 👎  📋               ← feedback + copy actions
└──────────────────────────────────┘
```

---

## 2. Operations Screen (`/operations`)

**Component**: `components/cockpit/operations/operations-screen.tsx`
**Role**: Execute system actions and monitor job execution

### Layout

```
┌─────────────────────────────────────────┐
│  Service Health Grid (3 badges)         │
├─────────────────────────────────────────┤
│  Action Bar                             │
│  [Ticker Input] [Action Select] [Run]   │
├──────────────────┬──────────────────────┤
│  Job List        │  Job Detail Panel    │
│  (scrollable)    │  (selected job)      │
│  ┌─────────┐     │  Status, output,     │
│  │ Job 1   │←    │  duration, errors    │
│  │ Job 2   │     │                      │
│  │ Job 3   │     │                      │
│  └─────────┘     │                      │
└──────────────────┴──────────────────────┘
```

### Key Patterns

- **Service health badges**: Color-coded (green/amber/red) for backend, GPU, model
- **Split panel**: `ResizablePanel` with drag handle between job list and detail
- **Real-time polling**: Jobs refresh every 1500ms
- **Action preview**: Shows arguments before execution
- **Stop capability**: Red destructive button with confirmation

### Available Actions

`daily_news_ingest`, `historical_news_ingest`, `daily_announcement_ingest`, `metric_extraction`, `rebuild_ticker_financials`, `audit_ticker_financials`, `single_ticker_announcement_backfill`, `show_candlestick`

---

## 3. Updater Screen (`/updater`)

**Component**: `components/cockpit/updater/updater-screen.tsx`
**Role**: Backfill and refresh ticker financial data

### Layout

```
┌─────────────────────────────────┐
│  Control Card                   │
│  [Ticker] [Year Range ▼]       │
│  ☐ Process Documents  [Fetch]   │
├─────────────────────────────────┤
│  Progress (if running)          │
│  ████████████░░░  67%           │
│  "Processing announcements..."  │
├─────────────────────────────────┤
│  Results Table                  │
│  Period | Revenue | Profit | .. │
│  2024H1 | $1.2M  | $340K  | .. │
├─────────────────────────────────┤
│  Audit Confidence               │
│  [████████░░] 82%  HIGH         │
└─────────────────────────────────┘
```

### Key Patterns

- **Ticker auto-uppercase**: Input transforms to uppercase on change
- **Year range selector**: Dropdown with 1/3/5/10 year options
- **Progress**: Indeterminate bar advancing to ~90% during fetch
- **Results table**: Financial metrics with formatted currency (`$1.2M`)
- **Audit confidence**: Progress bar + badge (HIGH/MEDIUM/LOW)

---

## 4. Verification Screen (`/verification`)

**Component**: `components/cockpit/verification/verification-screen.tsx`
**Role**: Document extraction quality review and evaluation

### Layout

```
┌─────────────────────────────────────────┐
│  Filter Bar                             │
│  [Search] [Date From] [Date To] [Method ▼] │
├─────────────────────────────────────────┤
│  Document List                          │
│  ┌────────────────────────────────────┐ │
│  │ Doc ID | Ticker | Date | Status   │ │
│  │ ▸ ASX-001 | BHP | 2026-01 | ✓    │ │
│  │   └─ Snippet preview              │ │
│  │   └─ Method: docling              │ │
│  │   └─ [Accept] [Reject]            │ │
│  │ ▸ ASX-002 | RIO | 2026-01 | ⚠    │ │
│  └────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│  Active Extraction Run (if any)         │
│  Run ID: xxx | Progress | TTL           │
└─────────────────────────────────────────┘
```

### Key Patterns

- **Expandable rows**: Click to reveal snippet images, method details
- **Snippet image states**: `idle → loading → ready` (with retry logic for slow generation)
- **Method override**: Dropdown to force specific extraction method (Auto/Docling/PyMuPDF/Anthropic)
- **Trust outcomes**: Color-coded badges — trusted (green), abstain (amber), quarantine (red)
- **Accept/Reject**: Decision buttons per document
- **Active extraction monitor**: Shows running extraction with TTL countdown

---

## 5. History Screen (`/history`)

**Component**: `components/cockpit/history/history-screen.tsx`
**Role**: Past job execution records

### Layout

```
┌─────────────────────────────────────────┐
│  [Filter by status ▼]                   │
├─────────────────────────────────────────┤
│  Job | Action | Status | Duration | Time│
│  ▸ job-001 | metric_extraction | ✓ | 4m │
│    └─ Output log...                     │
│  ▸ job-002 | news_ingest | ✗ | 12s     │
│    └─ Error: connection timeout         │
└─────────────────────────────────────────┘
```

### Key Patterns

- **Expand/collapse**: Chevron toggle reveals output or error logs
- **Status badges**: Running (spinner icon, animated), Completed (check, green), Failed (X, red)
- **Time display**: Relative ("3 hours ago") format
- **Rerun capability**: Button to re-execute a past job

---

## 6. Settings Screen (`/settings`)

**Component**: `components/cockpit/settings/settings-screen.tsx`
**Role**: Configuration display (mostly read-only)

### Layout

```
┌─────────────────────────────────────────┐
│  LLM Config Card                        │
│  model: qwen3:30b-a3b | endpoint: ...  │
│  routing: local_first | tokens: 4096    │
├─────────────────────────────────────────┤
│  Backend Config Card                    │
│  url: http://127.0.0.1:8000 | profile  │
├─────────────────────────────────────────┤
│  Features Card                          │
│  web_search: ON | rag: ON | extract: ON │
├─────────────────────────────────────────┤
│  Environment Card                       │
│  python: 3.12.x | branch: main | ...   │
└─────────────────────────────────────────┘
```

### Key Patterns

- **Card sections**: Grouped by domain (LLM, Backend, Features, Environment)
- **Monospace values**: Technical values in `font-mono text-[11px]`
- **Boolean toggles**: Displayed as ON/OFF badges
- **Model selector**: Only writable element — dropdown fetching available models

---

## 7. News Screen (`/news`)

**Component**: `components/cockpit/news/news-screen.tsx`
**Role**: Financial news search and filtering

### Layout

```
┌─────────────────────────────────────────┐
│  [Search query...] [Ticker filter]      │
├─────────────────────────────────────────┤
│  ▸ "BHP reports record iron ore output" │
│    Source: AFR | Relevance: 0.92        │
│    2 hours ago                          │
│    Preview snippet...           [Open ↗]│
│  ▸ "RIO quarterly production update"    │
│    Source: ASX | Relevance: 0.87        │
└─────────────────────────────────────────┘
```

### Key Patterns

- **Relevance score badge**: Numeric score with color intensity
- **External link**: Opens source in new tab
- **Collapsible previews**: Article content snippet
- **Relative timestamps**: "2 hours ago" format

---

## 8. Holdings Screen (`/holdings`)

**Component**: `components/cockpit/holdings/holdings-screen.tsx`
**Role**: Cockpit-local holdings management (CRUD + portfolio overview)

### Layout

```
┌─────────────────────────────────────────┐
│  Header + Portfolio Scope + Refresh     │
├─────────────────────────────────────────┤
│  KPI Strip (4 cards)                    │
│  Positions | Active | Accounts | Cost   │
├─────────────────────────────────────────┤
│  Holdings Exposure Card                 │
│  Amount/Percent | Line/Bar | D/M/Y      │
│  Derived chart (line or bar)            │
├─────────────────────────────────────────┤
│  Add Holding Card                       │
│  Ticker/Qty/Cost/Account + advanced     │
├─────────────────────────────────────────┤
│  Filter Card                            │
│  Search | Status Filter | Sort          │
├─────────────────────────────────────────┤
│  Holdings Ledger Table                  │
│  Row actions: Edit | Details | Remove   │
│  Expandable detail row for metadata      │
│  Footer pagination: Rows + Prev/Next    │
└─────────────────────────────────────────┘
```

### Key Patterns

- KPI summary cards with monospace metadata (`font-mono`) and status badges
- Portfolio-scoped view via header selector (All portfolios or account-specific)
- Jam-style segmented controls via `ToggleGroup`: `Amount/Percent`, `Line/Bar`, and `D/M/Y`
- Derived exposure chart rendered with shared `ChartContainer` + Recharts primitives
- Inline search/filter/sort over currently loaded holdings
- Expandable per-row detail panel (thesis bucket, currency, opened date, note, id)
- Paged ledger with configurable row density (10/25/50) and Prev/Next navigation
- Preserves existing backend contract via `/api/cockpit/holdings*` CRUD
- No light mode or palette changes; follows existing dark OKLch design tokens

---

## 9. Intel Pulse Screen (`/intel-ops`)

**Component**: `app/intel-ops/page.tsx`
**Role**: Real-time pipeline monitoring and failure diagnosis

### Layout

```
┌─────────────────────────────────────────────────┐
│  ScopeTerminal                                  │
│  [MODE: GLOBAL] [Search company...] [LIVE ●]    │
├─────────────────────────────────────────────────┤
│  PipelineRibbon                                 │
│  [Overview] [Extraction 92%] [Eval 87%] [Sig] [Mem] [Fail 3] │
├────────────────────────────────┬────────────────┤
│  Stage Panel (75%)             │ Inspector (25%)│
│                                │                │
│  DiagnosticMatrix              │ INSPECTOR_PANE │
│  ┌─────────────────────────┐   │ ─────────────  │
│  │     Rev  Prof  Cash EPS │   │ Status: LIVE   │
│  │ BHP  ●    ●    ○    ●  │   │                │
│  │ RIO  ●    ○    ●    ●  │   │ Raw metadata:  │
│  │ FMG  ○    ▲    ●    ○  │   │ { ... }        │
│  └─────────────────────────┘   │                │
│                                │ Trace:         │
│  Legend:                       │ [extract] ✓    │
│  ● Populated ○ Sparse          │ [evaluate] ✓   │
│  ▲ Abstained ✗ Failed          │ [store] ✓      │
│                                │                │
│  OR                            │ Linked:        │
│                                │ BHP.AX         │
│  FailureRegistry               │                │
│  ┌─────────────────────────┐   │ Notes:         │
│  │ ✗ ASX-001 extract fail  │   │ "From docling" │
│  │ ▲ ASX-002 eval reject   │   │                │
│  └─────────────────────────┘   │                │
└────────────────────────────────┴────────────────┘
```

### Key Patterns

- **Scope toggle**: Global system vs. single company mode
- **Pipeline ribbon**: Horizontal stage buttons with health % badges
- **Diagnostic matrix**: Entity x Metric grid with density-state coloring
  - `populated` → green bg (`oklch(0.69_0.22_145)`)
  - `abstain` → amber bg (`oklch(0.78_0.17_80)`)
  - `failed` → red bg (`oklch(0.58_0.22_25)`)
  - `sparse` → gray bg (`oklch(0.33_0.02_260)`)
- **Inspector pane**: Resizable, shows metadata JSON, trace timeline, linked entities
- **Failure registry**: Type-specific icons (FileX for extraction, ShieldX for evaluation)
- **30-second polling**: Auto-refresh for live monitoring
- **Keyboard navigation**: Number keys 1–8 for stage selection

### Stage Panel Components

| Stage | Component | Content |
|-------|-----------|---------|
| Overview | Population index, trust score, quarantine rate, compact failures |
| Extraction | `DiagnosticMatrix` showing extraction density |
| Evaluation | `DiagnosticMatrix` showing evaluation outcomes |
| Signals | Placeholder — future feature |
| Memory | Placeholder — future feature |
| Failures | Full `FailureRegistry` |

---

## 10. Boot Screen (`/boot`)

**Component**: `components/cockpit/boot/boot-screen.tsx`
**Role**: System health check and onboarding

### Key Patterns

- Health check sequence with progress indicators
- Service discovery and connectivity verification
- First-run configuration guidance

---

## Cross-Screen Patterns

### CockpitLayout (wraps all screens)

```
┌───┬─────────────────────────────────┐
│   │  Header (h-12)                  │
│ S │  [☰] | Page Title [TICKER]      │
│ I ├─────────────────────────────────┤
│ D │                                 │
│ E │  Main Content Area              │
│ B │  (flex-1, overflow-hidden)      │
│ A │                                 │
│ R │                                 │
│   ├─────────────────────────────────┤
│   │  CockpitStatusBar              │
│   │  [model] [tokens] [temp]       │
│   │  [extraction status] [health]  │
└───┴─────────────────────────────────┘
```

### Status Bar Content

Left to right:
1. Selected model badge
2. Active runtime model badge
3. Max tokens badge
4. Temperature badge
5. Route indicator (Claude API / local)
6. Extraction status (running with TTL / idle)
7. API override toggle (XL screens only)
8. Backend health dot + latency
9. Session cost

### Sidebar Content

- **Header**: Logo (Zap icon in primary bg) + "Financial Cockpit" / "Analysis Workstation"
- **Navigation**: 8 items with icons and keyboard shortcuts
- **System Status**: Backend health dot, GPU dialog trigger, config sync time, config summary box
- **Notices**: Critical/error/warning banners (auto-dismiss warnings at 8s)
- **Footer**: Service count badge + session cost

### Common Interaction Patterns

1. **Polling**: Health every 3s (healthy) or 15s (unhealthy), config every 30s, jobs every 1.5s
2. **Real-time updates**: SSE for chat streaming and job output
3. **Resizable panels**: `react-resizable-panels` for split layouts
4. **Collapsible sections**: Chevron-toggled expandable content
5. **Copy to clipboard**: Copy icon toggles to check icon on success
6. **Toast notifications**: Via `sonner` library
7. **Loading states**: `Skeleton` components for placeholder content
