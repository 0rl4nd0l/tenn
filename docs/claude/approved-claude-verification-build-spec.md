# Verification Screen — Refactor Build-Spec

## 1. SCREEN PURPOSE

**What this screen is for:** A trust-verification and extraction-audit workstation. Operators validate that the financial data extraction pipeline is producing correct, trustworthy outputs by inspecting per-metric evidence against source PDFs.

**Primary user types:**
- **Extraction operator** — runs extractions, reviews metrics, records verdicts
- **Quality auditor** — inspects gold-set evaluations, reviews wrong queues, exports audit artifacts

**Top user tasks (ranked):**
1. Review extracted metrics against PDF evidence and record verdicts (correct/wrong/unsure)
2. Run extraction for a document set and monitor progress
3. Inspect a historical run's timeline, warnings, and errors
4. Run gold-set evaluation and compare accuracy across extraction methods
5. Export audit artifacts (JSON, HTML reports)

---

## 2. CURRENT PROBLEMS

### UX problems
- **No tab navigation.** All 4 workflows (Review, Real-Gold, Run Timeline, Data Verification) are stacked vertically in a single scroll. The user must scroll past irrelevant cards to reach the workflow they need. _(Confirmed — lines 1338–2413 are one sequential column.)_
- **Evidence viewer is buried.** The review editor (the most-used section) appears at line 2054 — below config, verification, gold eval, manual review setup, session status, AND run timeline. An operator doing repeated C/W/U verdicts must scroll past ~700 lines of rendered cards to reach the evidence.
- **No persistent navigation context.** When scrolling into the review editor, the user loses sight of which ticker/method/session is active. The config card at the top scrolls off-screen.
- **Duplicate run-status rendering.** `ExtractionRunStatusCard` is rendered in both the Live Extraction Monitor card (line 1460) and the Manual Extraction Review card (line 1827) with slightly different title logic. Same data, two locations.
- **Visualization placeholder.** The "Visualization" card (lines 2388–2407) is a dead placeholder. It adds clutter without function.

### Information architecture problems
- **Mixed concerns in a single Card.** The "Manual Extraction Review" card (lines 1682–1849) contains: document loading, extraction triggering, run history, run inspection, error display, loading state, document table, selected review set summary, AND inline run status cards. This is ~170 lines of JSX in one CardContent.
- **Wrong Queue is always-visible.** The Wrong Queue card renders even when no review session exists. It shows an empty state that wastes vertical space. _(Confirmed — line 2347, no conditional guard.)_
- **Gold eval and verification results are peer-level.** Gold eval is a batch pipeline operation; data verification is a quick health check. They have different operational weight but identical visual hierarchy.

### Maintainability problems
- **2,413-line monolith.** One component owns all state, handlers, effects, refs, and JSX. _(Confirmed.)_
- **30+ `useState` declarations** (lines 454–494). No state is co-located with its consumers.
- **~40 helper functions** defined at module scope (lines 144–392). Many are pure utilities (formatting, parsing) mixed with domain logic (evidence quality computation, session summarization).
- **No custom hooks.** All data fetching is inline `async` functions inside the component body. No React Query. No abstraction boundary between "fetching" and "rendering."
- **Refs used as locks** (`documentLoadLockRef`, `reviewActionLockRef`, `recentRunsLoadLockRef`). These are manual concurrency guards that React Query's `isFetching`/`isPending` would handle automatically.
- **Polling implemented manually** (lines 716–754). `setInterval` + cancelled flag + manual status merging. React Query's `refetchInterval` does this with fewer bugs.

### State/data-flow problems
- **No query invalidation.** When a verdict is submitted, the session is patched locally (lines 1177–1184) rather than invalidating a query. If the PATCH response differs from expectations, the UI and server diverge silently.
- **LocalStorage used for active runs** (lines 623–628, 650–662). This is a fragile persistence layer — browser-dependent, no expiry, no cross-tab sync. It leaks stale run IDs.
- **Derived state computed inside render.** `currentReviewItem`, `activeRunId`, `matchedEvidenceText`, `currentSnippetUrl`, etc. (lines 514–548) are derived in the component body, recomputed on every render. Some are memoized, some aren't.
- **No error boundary.** A JSON parse failure in any handler would crash the entire screen.

### Operator-risk problems
- **No confirmation on destructive actions.** "Run Latest + Load Review" (line 1718) triggers extraction + session creation in one click. If the operator accidentally clicks it mid-review, the current session is cleared (`beginReviewSessionSwap`, line 610) with no undo.
- **Keyboard shortcuts are global.** `C`, `W`, `U` trigger verdicts (lines 1238–1244). If the user types in an input field that doesn't have proper tag filtering, a verdict could fire. The guard checks `tagName === 'input' || tagName === 'textarea'` but misses `contentEditable` elements and select components.
- **No stale-session warning.** If the backend extraction was re-run by another tab/user, the review session in-browser has no staleness check.

---

## 3. REFACTORED INFORMATION ARCHITECTURE

### Recommended page structure

```
VerificationScreen
├── VerificationHeader (persistent, never scrolls away)
│   ├── Active ticker + method + strict badge strip
│   ├── Session summary badges (when review session active)
│   └── Config popover trigger (opens extraction config editor)
│
├── VerificationTabBar (persistent)
│   ├── Review        (primary workflow)
│   ├── Gold Eval     (batch evaluation)
│   ├── Runs          (run history + timeline)
│   └── Verify        (quick data health checks)
│
├── [Active Tab Panel]  (scrollable content area)
│   └── (see section 4 for each tab's tree)
│
└── VerificationStatusStrip (persistent footer, optional)
    └── Wrong queue count + session progress + active run indicator
```

### Persistent vs tab-local

| Element | Persistent | Why |
|---------|-----------|-----|
| Ticker / method / strict config | Yes | All tabs use these inputs |
| Session summary badges | Yes | Operator needs to see progress at all times during review |
| Tab bar | Yes | Navigation must be always accessible |
| Review editor | Tab-local (Review tab) | Largest visual surface, needs maximum space |
| Gold eval results | Tab-local (Gold Eval tab) | Independent batch workflow |
| Run timeline | Tab-local (Runs tab) | Deep inspection, not needed during review |
| Verification results | Tab-local (Verify tab) | Quick health check, rarely referenced during review |
| Wrong queue count | Persistent (status strip) | Operator should see the count, but the detail list is tab-local or accessible from Review tab |

### Controls that should move to shared header

- **Active Ticker input** → persistent header (currently inside Extraction Configuration card)
- **Method / Strict toggles** → persistent header or config popover
- **Session badges** (pending/correct/wrong/unsure) → persistent header when review session active

### Provenance/evidence surfacing without clutter

- Evidence snippet viewer stays full-width in the Review tab's right panel
- Provenance details collapse into an expandable `<details>` section within the evidence viewer
- Evidence quality badge is always visible next to the metric in the left sidebar
- Method provenance (requested vs actual, parser, fallback) renders as a compact badge row, not a 2-column grid
- ASCII preview is collapsed by default (only useful for precise evidence debugging)

---

## 4. COMPONENT TREE

### Shell

**`VerificationScreenShell`**
- Purpose: Layout container with persistent header and tab router
- Props: none (reads from stores/hooks)
- State: owns `activeTab` (local state, persisted to URL search params)
- Reusable: no

### Persistent header

**`VerificationHeader`**
- Purpose: Shows active ticker, method, strict mode, session summary
- Props: `{ ticker, method, strictMethod, sessionSummary?, onConfigOpen }`
- State: receives state (stateless display component)
- Reusable: no

**`ExtractionConfigPopover`**
- Purpose: Popover form for editing ticker, method, strict mode, docs limit
- Props: `{ ticker, method, strictMethod, docsLimit, onChange }`
- State: local form state, calls parent onChange on submit
- Reusable: no

### Tab bar

**`VerificationTabBar`**
- Purpose: Horizontal tab strip (Review | Gold Eval | Runs | Verify)
- Props: `{ activeTab, onTabChange, wrongQueueCount?, pendingCount? }`
- State: stateless
- Reusable: yes (generic tab bar pattern)

### Review tab

**`ReviewTabPanel`**
- Purpose: Container for the extraction review workflow
- Props: none (uses hooks)
- State: orchestrates sub-components via `useReviewSession` hook
- Reusable: no

**`DocumentSelector`**
- Purpose: Load documents for a ticker, select primary + extra IDs
- Props: `{ ticker, docsLimit, onDocumentsLoaded }`
- State: owns `documents`, `selectedDocumentId`, `extraDocumentIds`
- Reusable: no (but extractable)

**`ReviewActionBar`**
- Purpose: Button row (Load Docs, Run Extraction, Run Latest + Load Review, Export)
- Props: `{ onLoadDocs, onRunExtraction, onLoadReview, onExport, isLoading, hasSession }`
- State: stateless
- Reusable: no

**`RunSelector`**
- Purpose: Select a recent run to inspect
- Props: `{ runs, selectedRunId, onSelect, onRefresh, onInspect, isLoading }`
- State: stateless
- Reusable: no

**`ReviewItemSidebar`**
- Purpose: Scrollable list of extracted metrics in the review session
- Props: `{ items, selectedItemId, onSelect }`
- State: stateless (selection managed by parent)
- Reusable: no

**`ReviewEvidencePanel`**
- Purpose: Evidence viewer — snippet image, provenance, matched text, verdict buttons
- Props: `{ item, evidenceQuality, snippetState, onVerdict, onPrev, onNext, hasPrev, hasNext, isLoading }`
- State: owns snippet image loading state (via `useSnippetImage` hook)
- Reusable: no

**`ProvenanceDetails`**
- Purpose: Expandable provenance section (method, parser, model, runtime, fallback)
- Props: `{ item }`
- State: stateless
- Reusable: yes (also used in Wrong Queue detail)

**`VerdictBar`**
- Purpose: Correct / Wrong / Unsure buttons + keyboard shortcut hint
- Props: `{ onVerdict, isLoading, isDisabled }`
- State: stateless
- Reusable: no

**`WrongQueueCard`**
- Purpose: Shows wrong-marked items for extractor hardening
- Props: `{ queue }`
- State: stateless
- Reusable: no

### Gold Eval tab

**`GoldEvalTabPanel`**
- Purpose: Container for gold-set evaluation workflow
- Props: none (uses hooks)
- State: orchestrates via `useGoldEval` hook
- Reusable: no

**`GoldEvalSummaryGrid`**
- Purpose: 4-column stat grid (docs, metric accuracy, context accuracy, trust matches)
- Props: `{ summary }`
- State: stateless
- Reusable: no

**`GoldEvalDocumentTable`**
- Purpose: Per-document gold eval results table
- Props: `{ documents, method }`
- State: stateless
- Reusable: no

### Runs tab

**`RunsTabPanel`**
- Purpose: Run history + timeline inspection
- Props: none (uses hooks)
- State: orchestrates via `useRunTimeline` hook
- Reusable: no

**`ExtractionRunStatusCard`** _(already exists, refactor to shared)_
- Purpose: Status card for a single extraction run
- Props: `{ documentId, runId, status?, title?, fallbackMethod }`
- State: stateless
- Reusable: yes

**`RunTimelineCard`**
- Purpose: Detailed timeline for a single run (timestamps, stage timings, events, warnings/errors)
- Props: `{ runStatus }`
- State: stateless
- Reusable: no

**`LiveExtractionMonitor`**
- Purpose: Shows active extraction runs attached from backend state
- Props: `{ runs, statuses, notice? }`
- State: stateless
- Reusable: no

### Verify tab

**`VerifyTabPanel`**
- Purpose: Quick data verification health checks
- Props: none (uses hooks)
- State: orchestrates via `useVerification` hook
- Reusable: no

**`VerificationResultsTable`**
- Purpose: Pass/fail table with export buttons
- Props: `{ results, ticker, onExportJson, onExportHtml }`
- State: stateless
- Reusable: no

---

## 5. STATE OWNERSHIP PLAN

### Global/shared state (Zustand `useCockpitStore`)
- `activeTicker` — already in store, used by Verification header
- No new global state needed

### Screen-level state (React context or lifted state in `VerificationScreenShell`)
- `activeTab: 'review' | 'gold-eval' | 'runs' | 'verify'` — synced to URL `?tab=`
- `ticker: string` — local override of `activeTicker`
- `extractionMethod: ExtractionMethod`
- `strictMethod: boolean`
- `docsLimit: string`

### Tab-local state (managed in hooks, scoped to tab panel)

**`useReviewSession()` hook**
- `reviewSession: ExtractionReviewSession | null`
- `selectedReviewItemId: string | null`
- `reviewError: string | null`
- `isLoading: boolean`
- `wrongQueue: ExtractionReviewErrorQueue | null`
- Derived: `reviewItems`, `currentReviewItem`, `currentReviewIndex`, `evidenceQuality`, `hasPrev`, `hasNext`
- Methods: `loadReview()`, `submitVerdict()`, `loadWrongQueue()`, `moveSelection()`

**`useGoldEval()` hook**
- `goldEval: RealGoldEvalResponse | null`
- `goldLimit: string`
- `isLoading: boolean`
- `error: string | null`
- Methods: `runGoldEval()`, `exportJson()`

**`useRunTimeline()` hook**
- `recentRuns: ExtractionReviewRunSummary[]`
- `selectedRunId: string`
- `runStatus: ExtractionReviewRunStatusResponse | null`
- `activeRunIdsByDocumentId: Record<string, string>`
- `runStatuses: Record<string, ExtractionReviewRunStatusResponse>`
- `isLoading: boolean`
- Methods: `loadRecentRuns()`, `inspectRun()`, `refreshRunStatuses()`

**`useVerification()` hook**
- `results: VerificationResult[] | null`
- `isRunning: boolean`
- `error: string | null`
- Methods: `runVerification(broad)`, `exportJson()`, `exportHtml()`

**`useSnippetImage()` hook**
- `state: SnippetImageState`
- Methods: `onLoad()`, `onError()`, `reset()`

### Server state (React Query)
- **Convert all API calls to React Query.** Each hook above wraps `useQuery` / `useMutation`.
- Query keys: `['extraction-review', 'session', sessionId]`, `['extraction-review', 'runs', ticker]`, `['extraction-review', 'run', runId]`, `['extraction-review', 'errors']`, `['gold-eval', method, limit]`, `['verification', ticker]`

### Query invalidation boundaries
- After `submitVerdict` → invalidate `['extraction-review', 'session', sessionId]` and `['extraction-review', 'errors']`
- After `loadReview` → invalidate `['extraction-review', 'session']` (all)
- After `runGoldEval` → no invalidation needed (response is self-contained)
- After `runExtraction` → invalidate `['extraction-review', 'runs', ticker]`

### Memoization
- `reviewItems` sort — `useMemo` on `reviewSession.items`
- `selectedReviewDocumentIds` parse — `useMemo` on `extraDocumentIds + selectedDocumentId`
- `selectedRunStatuses` join — `useMemo` on `activeRunIdsByDocumentId + runStatuses + selectedReviewDocumentIds`
- Evidence derivations (`currentSnippetUrl`, `matchedEvidenceText`, `evidenceQuality`) — `useMemo` on `currentReviewItem`

---

## 6. DATA FETCHING PLAN

### Query-to-tab mapping

| Query | Tab | Load strategy |
|-------|-----|---------------|
| `getTickerDocuments` | Review | On-demand (Load Docs button) |
| `createExtractionReviewSession` | Review | On-demand (mutation) |
| `getExtractionReviewSession` | Review | On-demand (retry on snippet error) |
| `submitExtractionReviewDecision` | Review | Mutation with optimistic update |
| `getExtractionReviewErrors` | Review | Eager after session load, lazy refresh |
| `getExtractionReviewRuns` | Review + Runs | On-demand, cached across tabs |
| `getExtractionReviewRunStatus` | Runs | On-demand + polling for active runs |
| `POST /api/extraction-eval/real-gold` | Gold Eval | On-demand (mutation) |
| `GET /api/context/verification` | Verify | On-demand |
| `GET /api/cockpit/config` | Runs (monitor mode) | On mount when `?attach=active` |

### Eager vs lazy
- **Eager:** Wrong queue loads immediately after any session creation. Active run statuses poll automatically.
- **Lazy:** Gold eval, verification, run timeline detail — all on-demand only.

### Polling behavior
- Active extraction runs: 2.5s interval (existing behavior, keep it). Use React Query `refetchInterval` conditioned on `status !== 'succeeded' | 'failed' | 'blocked'`.
- Stop polling when all active runs reach terminal state.
- No other polling.

### Loading states
- Each tab panel shows a full-panel skeleton while its primary data loads.
- Verdict submission shows a disabled state on buttons + spinner on the active button.
- Snippet image has its own 3-state loading indicator (loading → ready | retrying → failed). Keep existing logic.

### Error states
- Each tab panel renders an inline error banner (destructive/10 bg, AlertCircle icon) — match existing pattern.
- API errors surface the backend's `detail` message when available.
- Network failures show a generic message + retry button.

### Empty states
- Review tab with no session: "Set a ticker and load documents to begin reviewing extracted metrics."
- Gold eval with no results: "Run the gold set evaluation to see accuracy results."
- Runs tab with no runs: "Load recent runs for a ticker to inspect extraction history."
- Verify tab with no results: "Run verification to check extraction health."
- Wrong queue empty: "No wrong-marked extraction items yet." (existing text)

### Retry behavior
- All mutations: no automatic retry. Manual retry via button.
- All queries: React Query default (3 retries with exponential backoff).
- Snippet image: one automatic retry via session refresh (existing behavior, keep it).

### Tab-switch persistence
- React Query cache persists data when switching tabs. No re-fetch on tab return unless stale.
- `staleTime: 30_000` for run lists and wrong queue. `staleTime: Infinity` for session data (only invalidated on mutation).

---

## 7. UX / INTERACTION RULES

### Review tab

| State | Behavior |
|-------|----------|
| **Default** | Config header visible. Document table empty. Prompt: "Load documents for a ticker." |
| **Empty session** | Session loaded but 0 items. Show session diagnostics table + "Run Extraction Again" / "Retry Load Review" buttons. |
| **Loading** | Spinner in action bar. Evidence panel shows "Loading a fresh review session..." with cleared snippet. |
| **Active review** | Left sidebar: metric list. Right panel: evidence + verdict buttons. Header: session summary badges. |
| **Error** | Inline destructive banner below action bar. Does not clear the current session. |
| **Destructive actions** | "Run Latest + Load Review" clears the current session. Add a brief confirmation if a session with pending items exists: "This will clear your current session with N pending items. Continue?" _(Speculative — operator velocity may outweigh the safety concern. Confirm with user.)_ |
| **Trust decisions** | C/W/U buttons + keyboard shortcuts. Auto-advance to next item after verdict. |
| **Keyboard** | `C` correct, `W` wrong, `U` unsure, `←` prev, `→` next. Only active when no input/textarea focused AND no `evidenceSuspendMessage`. |

### Gold Eval tab

| State | Behavior |
|-------|----------|
| **Default** | Doc limit input + Run Gold Set button. Method/strict inherited from header. |
| **Loading** | Spinner + "Running the current extraction pipeline across the gold set..." |
| **Success** | Summary grid + document table. Export button enabled. |
| **Error** | Inline destructive banner. |

### Runs tab

| State | Behavior |
|-------|----------|
| **Default** | Run selector dropdown + Refresh Runs button. If `?attach=active`, auto-attach on mount. |
| **Active monitor** | Grid of `ExtractionRunStatusCard` components with live polling. |
| **Run timeline** | Selected run's full timeline (timestamps, stage timings, events, warnings, errors). |
| **Error** | Inline destructive banner. |

### Verify tab

| State | Behavior |
|-------|----------|
| **Default** | "Run Broad Verification" + "Verify Ticker" buttons. |
| **Loading** | Spinner. |
| **Success** | Summary stats (passed/failed/rate) + results table + export buttons. |
| **Error** | Inline destructive banner. |

### Operator safety
- Verdict buttons disabled while `reviewActionLoading` or `evidenceSuspendMessage` is truthy.
- "Run Latest + Load Review" disabled while a review action is loading.
- Keyboard shortcuts suppressed when any input is focused.

---

## 8. EVIDENCE + PROVENANCE DISPLAY RULES

### Evidence image display
- Full-width within the right panel, max height 360px, `object-contain`.
- 3-state overlay: loading spinner → image visible → failure message with reason.
- One automatic retry (refresh session) before showing failure. _(Confirmed existing behavior.)_
- Below the image: snippet file path in muted monospace text.

### Requested vs actual method
- Render as a compact badge row: `[actual: PyMuPDF] [strict] [parser: pymupdf_v3]`
- If fallback was used: add `[fallback: yes]` badge in secondary/warning variant.
- Do not repeat the method in both the badge row and the provenance grid. Choose one.

### Parser/model/runtime provenance
- Collapse into an expandable `<details>` element labeled "Full provenance".
- Default closed. Contains: actual_method, parser_id, model_id, runtime_id, fallback_used, error_stage, warnings.
- This keeps the evidence panel clean for rapid C/W/U triage while preserving full auditability.

### Confidence communication
- Evidence quality badge on every metric in the sidebar: `[precise]` green, `[approximate]` amber, `[missing]` muted.
- In the evidence panel: one-line headline ("Exact line evidence" / "Showing source page/table preview" / "No visual evidence available") + one-line body explanation.
- Do not repeat the quality explanation in three places (badge, headline box, and fallback message). Consolidate to badge + single explanation block.

### Dense audit readability
- Metric sidebar: metric name + extracted value + evidence quality badge + review status badge. 4 data points per row, no more.
- Evidence panel: value + period + document + provenance summary in a 2×3 grid. Expandable full provenance below.
- Remove duplicate rendering of `evidenceQualityHeadline` (currently rendered twice — lines 2208 and 2216).

---

## 9. ACCESSIBILITY + RESPONSIVENESS

### ARIA expectations
- Tab bar: `role="tablist"`, each tab `role="tab"` with `aria-selected`, panels `role="tabpanel"` with `aria-labelledby`.
- Review item sidebar: `role="listbox"`, each item `role="option"` with `aria-selected`.
- Verdict buttons: `aria-label` including the metric name ("Mark revenue_total as correct").
- Evidence image: existing `alt` text is adequate.

### Focus order
1. Config popover trigger → Tab bar → Active tab panel content
2. Within Review tab: Action bar → Document table → Run selector → Review item sidebar → Evidence panel → Verdict buttons
3. After verdict submission: focus returns to the next review item in the sidebar.

### Keyboard support
- Tab bar: `ArrowLeft`/`ArrowRight` to move between tabs (standard Radix tab behavior).
- Review: existing `C`/`W`/`U`/`←`/`→` shortcuts, guarded by input focus check. Add `contenteditable` and `[role="combobox"]` to the guard.
- Escape: close config popover if open.

### Announcements
- After verdict: `aria-live="polite"` region announces "metric_name marked correct. N pending remaining."
- After session load: announce "Review session loaded with N items."
- After error: announce error message.

### Smallest supported layout
- **Min width: 768px.** This is an operator workstation, not a mobile app. _(Inferred from existing `md:` breakpoints and `max-w-6xl` container.)_
- Below 1024px: Review tab switches from sidebar+panel to stacked layout (metric list above evidence panel).
- Below 768px: not officially supported, but tab bar should stack vertically and cards should be full-width.

### Collapse/stack behavior
- Review sidebar (320px) + evidence panel: side-by-side above `xl:` (1280px), stacked below.
- Gold eval summary grid: 4 columns above `md:`, 2 columns below.
- Run timeline timestamp grid: 4 columns above `xl:`, 2 columns below `md:`.

---

## 10. IMPLEMENTATION PLAN FOR CODEX

### Ordered refactor sequence

**Phase 1: Extract utilities and types (low risk)**
1. Move module-scope utility functions (lines 144–392) to `verification/utils.ts`.
2. Move local types (`RealGoldEvalMetricResult`, `RealGoldEvalDocument`, `RealGoldEvalResponse`, `ProcessDocumentResponse`, `SnippetImageState`, `ActiveExtractionMonitorRun`) to `verification/types.ts`.
3. Move `EXTRACTION_METHOD_OPTIONS` and `ACTIVE_RUNS_STORAGE_KEY` constants to `verification/constants.ts`.
4. Move `ExtractionRunStatusCard` to `verification/extraction-run-status-card.tsx`.
5. Verify: no behavior change, types resolve, no regressions.

**Phase 2: Extract custom hooks (medium risk)**
6. Create `verification/hooks/use-verification.ts` — extract `handleRunVerification`, export functions, and related state.
7. Create `verification/hooks/use-gold-eval.ts` — extract gold eval state + `handleRunGoldEval`.
8. Create `verification/hooks/use-run-timeline.ts` — extract run timeline state, polling, `handleLoadRecentRuns`, `handleInspectSelectedRun`, `refreshRunStatuses`.
9. Create `verification/hooks/use-review-session.ts` — extract review session state, `handleLoadReview`, `handleSubmitReview`, `loadWrongQueue`, `moveReviewSelection`, `beginReviewSessionSwap`.
10. Create `verification/hooks/use-snippet-image.ts` — extract snippet image state machine.
11. Create `verification/hooks/use-document-selector.ts` — extract document loading, selection, extraction triggering.
12. Verify: `VerificationScreen` now calls hooks instead of inline state. All existing behavior preserved.

**Phase 3: Extract tab panels (medium risk)**
13. Create `verification/tabs/verify-tab-panel.tsx` — uses `useVerification` hook.
14. Create `verification/tabs/gold-eval-tab-panel.tsx` — uses `useGoldEval` hook.
15. Create `verification/tabs/runs-tab-panel.tsx` — uses `useRunTimeline` hook.
16. Create `verification/tabs/review-tab-panel.tsx` — uses `useReviewSession`, `useDocumentSelector`, `useSnippetImage` hooks.
17. Verify: each tab renders identically to the original stacked cards.

**Phase 4: Add tab navigation (low-medium risk)**
18. Create `verification/verification-header.tsx` — persistent ticker/method/strict display.
19. Create `verification/verification-tab-bar.tsx` — Radix Tabs wrapping the 4 panels.
20. Create `verification/verification-screen-shell.tsx` — compose header + tab bar + panels.
21. Replace the monolith `VerificationScreen` with `VerificationScreenShell`.
22. Sync `activeTab` to URL `?tab=review|gold-eval|runs|verify`.
23. Verify: all 4 workflows accessible via tabs, no data loss on tab switch.

**Phase 5: Extract sub-components within tabs (low risk)**
24. Extract `ReviewItemSidebar`, `ReviewEvidencePanel`, `VerdictBar`, `ProvenanceDetails` from `ReviewTabPanel`.
25. Extract `GoldEvalSummaryGrid`, `GoldEvalDocumentTable` from `GoldEvalTabPanel`.
26. Extract `RunTimelineCard`, `LiveExtractionMonitor` from `RunsTabPanel`.
27. Extract `VerificationResultsTable` from `VerifyTabPanel`.
28. Extract `ExtractionConfigPopover` from `VerificationHeader`.

**Phase 6: Migrate to React Query (higher risk, highest value)**
29. Replace inline fetch calls in each hook with `useQuery`/`useMutation`.
30. Remove manual lock refs (`documentLoadLockRef`, etc.) — replaced by `isPending`.
31. Replace manual polling `setInterval` with `refetchInterval`.
32. Add query invalidation after mutations.
33. Verify: all data fetching works, polling stops on terminal states, tab switch preserves cache.

**Phase 7: Cleanup**
34. Remove the Visualization placeholder card.
35. Consolidate duplicate evidence quality rendering.
36. Add ARIA attributes to tab bar and review sidebar.
37. Delete the original monolith file once the shell is stable.

### What must remain unchanged during refactor
- All 10+ API endpoints and their request/response shapes
- Keyboard shortcuts (C/W/U/←/→)
- Evidence quality computation logic
- Snippet image retry behavior
- LocalStorage persistence for active runs (until Phase 6 replaces it)
- Session summary badge semantics
- Export artifact format (JSON and HTML)

### Likely regression risks
- **Snippet image loading race conditions.** The current `latestEvidenceKeyRef` + stale closure guard (lines 806–835) is subtle. The extracted `useSnippetImage` hook must preserve this exact race-condition defense.
- **Active run polling stoppage.** The current effect (lines 716–754) checks terminal states to stop polling. If the dependency array changes during extraction, polling may leak.
- **Review item auto-advance.** After submitting a verdict, the current item advances to `nextSelectedItemId` (line 1165). If the hook boundary introduces a render cycle between session update and selection update, the evidence panel may flash.

### Suggested test targets
- `useReviewSession`: verdict submission advances to next item, session summary updates correctly, wrong queue refreshes after verdict.
- `useSnippetImage`: image load success, image error triggers retry, stale key guard prevents race conditions.
- `useRunTimeline`: polling starts for active runs, stops for terminal states.
- `ReviewTabPanel`: keyboard shortcuts fire correct verdicts, shortcuts suppressed in input fields.
- `VerificationScreenShell`: tab switching preserves query cache, URL syncs with active tab.
- `ExtractionRunStatusCard`: renders status, stage, method, elapsed correctly.
- Export functions: JSON and HTML output match expected format.

---

## 11. ACCEPTANCE CRITERIA

1. **Tab navigation works.** User can switch between Review, Gold Eval, Runs, Verify tabs. Active tab persists in URL `?tab=`. Page reload restores the correct tab.
2. **No data loss on tab switch.** Switching from Review to Gold Eval and back preserves the review session, selected item, and verdict progress.
3. **Review workflow unchanged.** Load Docs → select document → Run Latest + Load Review → review items → C/W/U verdicts → next item auto-advance. All steps produce identical API calls and identical UI behavior as the monolith.
4. **Keyboard shortcuts work.** C/W/U/←/→ fire in Review tab. Suppressed when input/textarea/select focused. Do not fire in other tabs.
5. **Snippet image lifecycle unchanged.** Loading → ready | retrying → failed. Automatic session refresh on first error. Stale key guard prevents cross-item image leaks.
6. **Gold eval workflow unchanged.** Set doc limit → Run Gold Set → summary grid + document table renders. Export JSON works.
7. **Run timeline workflow unchanged.** Load Recent Runs → select run → Inspect Selected Run → timeline renders with timestamps, stages, events, warnings, errors.
8. **Active run polling works.** When runs are active, status updates every 2.5s. Polling stops when all runs reach terminal state.
9. **Persistent header shows active config.** Ticker, method, strict mode, and session summary badges visible at all times.
10. **No file exceeds 400 lines.** Each extracted component, hook, and utility file stays within the 200–400 line target.
11. **All existing API calls preserved.** No new endpoints. No changed request/response shapes. No backend changes required.
12. **Wrong queue renders.** Count visible in status area. Detail list accessible from Review tab.
13. **Export artifacts unchanged.** JSON and HTML verification reports produce identical output format.
14. **ARIA attributes present.** Tab bar uses `role="tablist"`, review sidebar uses `role="listbox"`, verdict buttons have `aria-label`.

---

## 12. OUT OF SCOPE

- **Backend API changes.** No new endpoints, no changed contracts, no schema migrations.
- **Other cockpit screens.** Chat, Operations, Settings, Updater, History, News, Intel Pulse — untouched.
- **Shared component library changes.** No modifications to `components/ui/` shadcn primitives.
- **Zustand store restructuring.** `useCockpitStore` is not modified (only consumed).
- **Visualization implementation.** The placeholder card is removed, not replaced. Charting is a separate feature.
- **Mobile layout.** Min supported width remains 768px. No mobile-first redesign.
- **Dark/light theme toggle.** Cockpit is dark-mode only by design.
- **Authentication/authorization.** No changes to API key handling.
- **React Query provider setup.** `QueryProvider` already exists in the root layout.
- **New Next.js routes.** The `/verification` page route stays as-is. Only the component tree inside it changes.
- **Test infrastructure.** Playwright config is not modified. New unit tests use the existing test runner.
