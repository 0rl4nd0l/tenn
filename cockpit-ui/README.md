# Cockpit Frontend (cockpit-ui)

The Cockpit Frontend is a modern, high-performance "Observable AI" workstation built for financial analysis and operational diagnostics. It is built on a Next.js 16 stack and is designed for power users who require deep transparency into AI reasoning and data integrity.

## Architecture & Technical Foundation

*   **Framework:** Next.js 16 (App Router)
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS 4 (using modern OKLCH color spaces) with a "Command Center" dark-mode aesthetic.
*   **Typography:** Standardized on `Fira Sans` (sans-serif) and `Fira Code` (monospace) for a consistent technical look.
*   **State Management:** 
    *   **Zustand:** Used for persistent UI state (ticker selection, feature toggles) and a persistent Execution Log buffer (up to 1000 entries) that survives page reloads.
    *   **TanStack Query:** Used for robust data fetching, caching, and background synchronization.
*   **Communication:** A specialized `api-client` handles standard REST requests and Server-Sent Events (SSE) for real-time streaming of chat responses and job logs. The client automatically syncs backend health status with the global store.
*   **Components:** Built on Radix UI and Shadcn primitives.

## Key Features

*   **Chat (`/chat`):** A streaming interface with expandable reasoning traces and tool execution timelines. Features "Action Previews" requiring explicit user confirmation before critical operations.
*   **YouTube/Commentary Attachments (frontend slice):** The chat screen now detects pasted YouTube URLs, renders an ingest summary card, keeps per-tab attached-source state, and can surface takeaways/watchlist UI when the matching backend commentary endpoints are available. This is still backend-dependent: the web client does not own ingest, retrieval, or watchlist truth.
*   **Intel Pulse (`/intel-ops`):** A high-density diagnostic grid visualizing the "density" of extracted data across entities using a custom color-coded status matrix.
*   **Operations (`/operations`):** Resource-aware job management (GPU/Host monitoring) with non-blocking execution and live log streaming. The UI is streamlined with a unified "Action Executor".
*   **Verification (`/verification`):** A Human-in-the-Loop (HITL) system for auditing AI extractions. Features side-by-side PDF snippet comparison and optimized keyboard shortcuts. Extraction settings are managed via a single, global configuration card to prevent clutter.
*   **Watchlist (`/watchlist`):** A dedicated screen and sidebar entry now exist in the web UI. Manual add/remove and commentary-driven add flows are wired through same-origin proxy routes and depend on backend `watchlist` endpoints being present.
*   **Offline Resilience:** A global `OfflineIndicator` automatically detects backend connection failures (e.g., 503 errors or network drops) and provides a "Cockpit Offline" warning with a manual retry mechanism.

## Testing Setup

The project now includes:

*   **Vitest + Testing Library** for fast component and hook coverage.
*   **Playwright** for end-to-end browser coverage.

### Running Tests

To run the unit/component suite:

```bash
pnpm test
```

To run the Playwright tests against the production build (recommended for stability due to Next.js Turbopack filesystem speed issues in some environments):

```bash
# 1. Build the application
pnpm run build

# 2. Run the Playwright tests
pnpm run test:e2e
# Or run with the UI mode
pnpm run test:e2e:ui
```

### Test Suites

*   **Vitest component tests:** Cover `useAttachedSources`, YouTube URL detection, `IngestSummaryCard`, `TakeawaysPanel`, `SourcesDrawer`, `CitationLink`, and `WatchlistScreen`.
*   **Smoke Tests (`tests/smoke.spec.ts`):** Verifies basic loading, title, sidebar rendering, and module navigation.
*   **Offline Resilience (`tests/offline.spec.ts`):** Uses Playwright's network mocking (`route.fulfill` and `route.abort`) to simulate backend outages and verify the UI correctly displays the `OfflineIndicator` and recovers when the backend returns to health.

## Recent Upgrades

*   **Frontend YouTube ingest scaffolding:** Added commentary/watchlist proxy route handlers under `app/api/cockpit/`, reusable proxy helpers in `lib/proxy.ts`, per-tab attached-source state, and chat-side ingest/takeaway/watchlist UI components. Full end-to-end behavior still requires backend support for `/api/commentary/takeaways`, `/api/commentary/recent`, `/api/commentary/ephemeral-index`, `/api/watchlist`, and `attached_sources` handling in `/api/cockpit/chat`.
*   **Watchlist navigation:** Added a top-level `Watchlist` route and sidebar entry backed by the new web screen and add/remove dialog.
*   **Frontend unit-test harness:** Added `vitest.config.ts`, `vitest.setup.ts`, and component tests so new cockpit-ui surfaces can be validated without relying only on Playwright.
*   **UI Consolidation:** Redundant "Service Health" and "Hardware Status" cards were removed from the Operations page, centralizing health monitoring in the global Status Bar and Offline Indicator. Duplicate extraction configuration inputs were removed from the Verification page in favor of a single global settings card.
*   **Persistent Audit Trail:** The `useLogBufferStore` persists execution logs to `localStorage` via Zustand, ensuring critical operational history is not lost on accidental refresh.
*   **Typography Fix:** Replaced conflicting generic `Geist` fonts with the project's standard `Fira Sans` and `Fira Code`.
