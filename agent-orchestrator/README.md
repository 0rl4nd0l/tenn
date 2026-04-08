# Agent Orchestrator

Local-agent-first kanban/orchestration control plane for coding agents.

## What It Is

This app keeps the main chat agent in a strategist role and delegates actual work through routed
tasks. It combines:

- deterministic orchestration code
- provider/runtime adapters over installed CLIs and products
- token-aware routing and session policy
- worktree-per-write-task isolation
- a kanban UI with strategist chat, logs, review, and routing visibility

## V1 Shape

Backend:

- Node.js + TypeScript
- SQLite state plus append-only event log
- scheduler, router, spawner, janitor, merge/review queue
- adapters for Codex local, Codex Cloud, Claude Code, Gemini CLI, Cursor, OpenCode, and a generic
  path

Frontend:

- React + TypeScript
- WebSocket-fed dashboard
- strategist chat
- kanban board
- task details, logs, review controls, and routing/token indicators

## Commands

Use the Node 16 toolchain already present in this workspace.

```bash
cd agent-orchestrator
npm install
npm run dev
```

Build, test, and smoke-check:

```bash
npm run build
npm run test
npm run smoke
```

Production-style start after build:

```bash
npm start
```

The HTTP server defaults to `127.0.0.1:4317`.

Runtime paths default to the checked-out `agent-orchestrator/` app directory for local state and
its parent workspace root for repo intelligence/worktrees. Override them only with:

```bash
AGENT_ORCHESTRATOR_APP_ROOT=/abs/path/to/agent-orchestrator
AGENT_ORCHESTRATOR_WORKSPACE_ROOT=/abs/path/to/workspace
AGENT_ORCHESTRATOR_DATA_DIR=/abs/path/to/data
```

## How V1 Works

- The strategist chat creates a parent planning record plus delegated child tasks.
- The router evaluates runtime candidates against task type, capability support, and token headroom.
- Write tasks default to isolated git worktrees and ownership locks.
- Deterministic janitor checks run before tasks move into review or completion.
- Review actions let you retry, reassign, reopen, approve, or reject tasks from the UI.

## Notes

- The strategist is read-only by default.
- Write tasks are expected to run in isolated worktrees with ownership locks.
- State persistence uses the bundled `sql.js` dependency. No host `sqlite3` CLI is required.
- Adapter telemetry quality varies by runtime, so the router tracks confidence and can fall back to
  estimated token accounting.
- See [ADR-0001](./docs/adr-0001-local-agent-first-architecture.md) for the baseline architecture
  decision.

## Known Gaps

- Some runtimes, especially Cursor and OpenCode, use conservative command assumptions and estimated
  telemetry because their CLI/headless surfaces are less uniform than Codex and Claude.
- Codex Cloud tasks require an environment id in task constraints before the cloud adapter can
  execute real work.
- Merge approval intentionally refuses to auto-merge when the repo root is already dirty. That keeps
  serialized merge policy deterministic instead of forcing unsafe local merges.
- The smoke check disables automatic task execution on purpose. It validates strategist planning,
  persistence, and state plumbing without launching external agent CLIs during local verification.
- Session strategies such as true in-session compaction or resume are not fully implemented yet.
  V1 routes and budgets with those concepts in mind, but execution still prefers fresh delegated
  runs for determinism.
