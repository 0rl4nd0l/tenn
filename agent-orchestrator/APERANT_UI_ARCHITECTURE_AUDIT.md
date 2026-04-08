# APERANT UI Architecture Audit

## Scope
- External comparison target audited in separate workspace: `/tmp/aperant-comparison/Aperant`
- Current product files audited for fit/gap analysis:
  - `agent-orchestrator/src/web/App.tsx`
  - `agent-orchestrator/src/web/components/StrategistPane.tsx`
  - `agent-orchestrator/src/web/components/ExecutionOverview.tsx`
  - `agent-orchestrator/src/web/components/KanbanBoard.tsx`
  - `agent-orchestrator/src/web/components/TaskDetailPane.tsx`
  - `agent-orchestrator/src/web/components/HeaderBar.tsx`
  - `agent-orchestrator/src/web/hooks/useOrchestratorState.ts`
  - `agent-orchestrator/src/server/api/state.ts`

## Confirmed From Code (Aperant)

### App Shell Structure
- Monorepo workspace with Electron desktop app in `apps/desktop`:
  - `/tmp/aperant-comparison/Aperant/package.json`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/package.json`
- Electron main entry and boot orchestration:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/index.ts`
- Renderer root shell and view switching:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/App.tsx`
- Sidebar-driven navigation model:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/Sidebar.tsx`

### Navigation Model
- Primary nav is explicit multi-view switching (`kanban`, `terminals`, `insights`, `roadmap`, `ideation`, `worktrees`, etc.) with keyboard shortcuts:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/Sidebar.tsx`
- Active view state held in renderer app shell (`activeView`):
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/App.tsx`
- Project tab bar provides multi-project context switching in same shell:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/App.tsx`

### Primary State Containers
- Renderer uses Zustand stores by domain:
  - Task state: `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/task-store.ts`
  - Terminal/session state: `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/terminal-store.ts`
  - Project state: `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/project-store.ts`
- Shared view flags via React context:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/contexts/ViewStateContext.tsx`

### Task Lifecycle Model
- Kanban is central execution surface with column states, DnD, queue/capacity behaviors:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/KanbanBoard.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/task-store.ts`
- Task detail is modal-based, tabbed, with start/stop/review/merge/discard operations:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/task-detail/TaskDetailModal.tsx`

### Terminal / Session Model
- Terminal grid with session restore, date-based replay, task association, project scoping:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/TerminalGrid.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/terminal-store.ts`
- XState actors are used for terminal machine behavior:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/terminal-store.ts`

### Worktree UX Model
- Dedicated worktrees view supports listing, merge, discard, PR creation, bulk selection:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/Worktrees.tsx`
- Task worktree operations exposed through task API and handlers:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/api/task-api.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-handlers/task/index.ts`

### Renderer ↔ Electron Main Data Flow
- Preload exposes unified `electronAPI` via context bridge:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/index.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/api/index.ts`
- IPC registration is modular by domain and wired from main startup:
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-setup.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-handlers/index.ts`

## Confirmed From Code (Current Project)
- Current UI is web-first, single-shell, strategist + overview/board + right detail rail:
  - `agent-orchestrator/src/web/App.tsx`
- State is fetched from backend board/task endpoints with websocket refresh + polling fallback:
  - `agent-orchestrator/src/web/hooks/useOrchestratorState.ts`
- Overview already has plan/run/review timeline semantics with live/stale distinction:
  - `agent-orchestrator/src/web/components/ExecutionOverview.tsx`
- Header includes summary counters, stream state, and view toggle:
  - `agent-orchestrator/src/web/components/HeaderBar.tsx`
- Server state payload for board/detail is assembled without frontend-specific coupling:
  - `agent-orchestrator/src/server/api/state.ts`

## Material Differences
- Aperant is desktop/Electron with broad feature-nav and rich local process/session control in renderer.
- Current project is web app over existing orchestrator backend with authoritative task/session truth in server payloads.
- Aperant task model is kanban-first execution UI; current target product is strategist-first with truthful latest-plan execution visibility.
- Aperant terminals/worktrees are first-class primary views; current product keeps task detail rail + board as secondary inspection.

## Inferred From Structure (Not Explicitly Proven in Single File)
- Aperant’s deep IPC and renderer-local store architecture likely assumes tighter coupling between UI and local execution substrate than current web app needs.
- Direct shell replacement in current web app would require an adapter layer to preserve existing strategist/router/scheduler/janitor semantics.

## AGPL-Sensitive Reuse Boundaries
- External repo is AGPL-3.0 licensed (`README.md`, `package.json`, `apps/desktop/package.json`).
- Safe reuse lane:
  - Interaction patterns, information architecture, state-shaping ideas, UX sequencing.
- Sensitive lane:
  - Copying implementation code, store logic, IPC contracts, component internals.
- Migration guidance:
  - Re-implement patterns natively in current codebase; do not transplant AGPL code into current project unless full license implications are accepted and documented.
