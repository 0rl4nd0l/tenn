# Project Agent Rules

Use this file as the authoritative Codex context for `financial-engine_v2` tasks.

## Session Context
- Repository focus: ASX ingestion and retrieval platform (financial-engine-v2)
- Primary runtime: `financial-engine-v2`
- Active branch/commit context is tracked in `~/.codex/config.toml` under `project.agent_context`

## Operating Rules
- Keep edits scoped to the current task; avoid unrelated churn.
- Prefer existing code patterns and config shape in `financial-engine_v2`.
- Do not revert user changes unless explicitly asked.
- Avoid destructive git operations (`git reset --hard`, `git checkout --`) unless explicitly requested.
- Do not run tests unless explicitly requested.
- Preserve existing behavior unless the task is to change it.

## Useful Local References
- `financial-engine_v2/backend/app/config/model_routing.yaml`
- `financial-engine_v2/backend/tests/test_model_routing.py`

## Runtime and Model Rules
- Runtime default: `financial-engine-v2`
  - Keep edits within this runtime unless explicitly asked to touch another workspace.
  - Prefer existing config-driven paths over hardcoded defaults (for routing, ingestion, and persistence settings).
  - Avoid broad architecture changes unless explicitly requested.
- Model default: `gpt-5.4`
  - Use concise, direct outputs and avoid speculative changes.
  - Prioritize actionable steps and concrete file changes over broad prose.
  - Maintain strict boundary: only run tests when explicitly requested.

## How Codex Uses This
- This file is a manual handoff reference.
- For automatic persistence across sessions, keep this file in sync with `~/.codex/config.toml`.
