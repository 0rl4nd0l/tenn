# ADR-0001: Local-Agent-First Orchestrator Architecture

## Status
Accepted

## Context

This repository does not already contain a TypeScript orchestration product. The existing repo is a
Python finance workspace, so the orchestrator needs a clean boundary instead of being embedded into
the current runtime.

The product requirements are:

- the main chat agent is a strategist and dispatcher, not the primary code-writing worker
- orchestration is deterministic code first
- runtime/provider integration happens through installed CLIs and products, not raw provider APIs
- routing is recursive and token-aware
- write tasks run in isolated worktrees with file ownership and merge gates
- the UI must expose strategist chat, kanban, logs, review, routing rationale, and token state

## Decision

Build a standalone `agent-orchestrator/` application with three code roots:

- `src/server`: deterministic control plane, adapters, storage, worktree/process control, API
- `src/shared`: shared contracts for tasks, sessions, routing, token budgets, and UI payloads
- `src/web`: React UI over HTTP and WebSocket state streams

The backend owns:

- task DAG and kanban state
- recursive routing and execution plan generation
- adapter capability snapshots
- token budget accounting and policy bands
- scheduler, spawner, janitor, merge queue, and worktree management
- append-only event log plus relational SQLite state

The frontend is observational and command-driven. It does not bypass orchestration logic.

## Consequences

Positive:

- preserves the existing finance workspace without coupling it to a new runtime stack
- keeps provider/runtime integration behind a stable adapter contract
- supports deterministic review and merge policy even when execution is parallel
- makes it practical to extend to additional runtimes and richer UI later

Tradeoffs:

- a new standalone app means separate package management and build steps
- some adapter telemetry will rely on estimates when CLIs do not expose rich stats
- V1 focuses on a strong end-to-end slice rather than exhaustive provider-specific depth
