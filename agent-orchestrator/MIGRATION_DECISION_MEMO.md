# Migration Decision Memo: Aperant Comparison

## Decision
- Recommendation: **use Aperant as a design/state-pattern reference, not a direct fork base**.
- Secondary recommendation: **selective pattern mining with clean-room reimplementation** in the current project.
- Do not adopt wholesale Electron architecture until a separate product decision approves desktop-first delivery.

## Why This Path
- Current backend already has strategist/router/scheduler/spawner/janitor/merge semantics and state contracts.
- Product gap is interaction quality and truthfulness of live state, not missing orchestration primitives.
- Direct fork would force high-risk re-plumbing of task/session/worktree ownership and increase licensing exposure (AGPL).

## Fit Mapping (Aperant → Current Product Need)
- Strategist chat
  - Aperant: insights/ideation surfaces, task creation flows.
  - Current need: strategist-first landing + concrete interpretation of vague engineering prompts.
  - Fit: **interaction pattern only**.
- Execution timeline / lane visibility
  - Aperant: strong kanban and status lanes.
  - Current need: truthful plan/run/review timeline scoped to latest request.
  - Fit: **lane and prioritization pattern**, not component code.
- Task inspection
  - Aperant: modal detail tabs with actionable controls.
  - Current need: persistent right rail with stale-safe detail loading.
  - Fit: **detail information architecture pattern**.
- Worktree visibility
  - Aperant: dedicated worktree page with merge/discard/PR actions.
  - Current need: surface worktree status without dominating default strategist flow.
  - Fit: **secondary inspection view pattern**.
- Terminal/session observability
  - Aperant: rich terminal sessions and restore flows.
  - Current need: truthful live session signal and non-misleading running state.
  - Fit: **session truth model and badges pattern**.
- Review/merge UX
  - Aperant: explicit review actions in task detail/worktrees.
  - Current need: deterministic janitor/review integration with current task graph.
  - Fit: **review action grouping pattern**.

## Gaps To Implement In Current Product
- Strategist-first landing and interpretation-first delegation behavior.
- Explicit live vs stale/orphaned state semantics in header + overview.
- Latest-request/plan scoping for default overview panes.
- Runtime/session truth alignment so “running” never implies live activity when no live session exists.
- Review/failure prioritization that favors current-plan and recent items by default.
- Secondary surfaces for board/worktree diagnostics without overwhelming default overview.

## Architecture Path Options
- Option A: Embed current backend behind new Electron shell now.
  - Status: **not recommended as first migration step**.
  - Risk: high coupling, state duplication, larger QA surface.
- Option B: Port selected Aperant renderer patterns into current web app.
  - Status: **recommended now**.
  - Risk: low-to-medium, reversible, preserves backend contracts.
- Option C: Incremental desktop migration after UX/state model is stable in web.
  - Status: **possible later milestone**.
  - Risk: medium; defer until product and distribution decisions are explicit.

## Risks
- License risk if AGPL code is copied directly.
- Semantic drift risk if UI introduces client-side lifecycle assumptions not backed by server truth.
- Trust risk if overview/headline counters overstate live activity.
- Scope creep risk if shell rewrite begins before phased checkpoint completion.

## License Caveats
- Aperant is AGPL-3.0.
- This evaluation treats it as reference architecture.
- Any direct code reuse requires explicit licensing decision and downstream obligations.
- Default implementation strategy must be pattern-inspired, code-independent reimplementation.

## Smallest Viable Integration Strategy
1. Keep existing backend and API contracts unchanged.
2. Continue strategist-first web shell and tighten truth semantics first.
3. Add minimal navigation/surface affordances inspired by Aperant only where they improve inspection flow.
4. Defer desktop-shell decisions until UX/state model is proven and documented in current app.

## Exact Aperant Modules Most Relevant
- App shell/layout
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/App.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/Sidebar.tsx`
- Kanban
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/KanbanBoard.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/task-store.ts`
- Task detail
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/task-detail/TaskDetailModal.tsx`
- Terminal panes
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/TerminalGrid.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/terminal-store.ts`
- Worktree/project selection
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/components/Worktrees.tsx`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/renderer/stores/project-store.ts`
- Global state + IPC/data flow
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/index.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/api/index.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/preload/api/task-api.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-setup.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-handlers/index.ts`
  - `/tmp/aperant-comparison/Aperant/apps/desktop/src/main/ipc-handlers/task/index.ts`
