# Implementation Phase Plan

## Phase 0: Analysis Checkpoints
- Confirm comparative architecture and state-flow boundaries are documented.
- Freeze migration decision:
  - no direct AGPL code import,
  - pattern-level reuse only,
  - backend orchestration semantics preserved.
- Confirm first-step change is reversible and isolated.
- Exit criteria:
  - `APERANT_UI_ARCHITECTURE_AUDIT.md` complete,
  - `MIGRATION_DECISION_MEMO.md` complete,
  - this phase plan complete.

## Phase 1: Shell/Layout Adoption (Selective, Web App)
- Goal: strengthen strategist-first shell while preserving board and detail inspection.
- Work items:
  - keep overview default landing,
  - keep board as secondary view,
  - tighten shell affordances for view switching and diagnostics placement.
- Constraints:
  - no backend contract changes,
  - no task graph semantic changes.
- Exit criteria:
  - build passes,
  - keyboard/textarea strategist flow unchanged,
  - selected task detail behavior unchanged.

## Phase 2: Task/State Truthfulness Fixes
- Goal: ensure visible execution state matches live session reality.
- Work items:
  - running counters reflect live-session-backed activity,
  - stale/orphaned running tasks clearly labeled,
  - historical failures demoted behind current-plan/recent items.
- Constraints:
  - websocket/polling behavior unchanged,
  - no DB schema changes.
- Exit criteria:
  - no misleading “running” in default overview when no live sessions exist unless explicitly labeled.

## Phase 3: Strategist-First Flow Integration
- Goal: improve strategist interpretation and actionability.
- Work items:
  - treat vague repo-grounded engineering requests as actionable discovery/verification intents,
  - default to read-only delegation for exploratory asks,
  - keep direct-answer behavior for assessment-only queries,
  - remove internal mode taxonomy from standard replies.
- Constraints:
  - preserve orchestrator/router/scheduler wiring semantics.
- Exit criteria:
  - “use agents to run repo analysis” yields concrete discovery plan/delegation,
  - “test pdf accuracy” yields concrete verification/discovery interpretation.

## Phase 4: Delegated Runtime + Review UX
- Goal: improve inspection depth without regressing strategist-first default.
- Work items:
  - strengthen task-detail grouping for run/review/route signals,
  - expose diagnostics/worktree context as secondary inspection surfaces,
  - maintain truthful freshness indicators across overview and detail.
- Constraints:
  - no broad shell rewrite until explicit migration decision refresh.
- Exit criteria:
  - improved operator trust in live status and review readiness with minimal cognitive load.

## First Validated Step (This Iteration)
- Implement a minimal, reversible strategist-shell fit change in current web app only.
- Follow immediately with strategist intent handling hardening for discovery/PDF verification interpretation.
- Validate with project build and targeted behavior checks.
