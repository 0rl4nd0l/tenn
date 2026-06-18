# Ledger Runtime

## Implemented

`scripts/agent_task_ledger.py` implements:

- `resolve-path`
- `validate`
- `append`
- `search`
- `summarize`
- `export-summary`

## Schema

Required fields:

- `task_id`
- `parent_task_id`
- `workflow`
- `status`
- `started_at`
- `updated_at`
- `owner`
- `session_id`
- `thread_id`
- `codex_goal_id`
- `source_session_ref`
- `issue_refs`
- `pr_refs`
- `branch`
- `worktree`
- `base`
- `files_touched`
- `artifacts`
- `summary`
- `validation`
- `next_action`
- `owner_boundary`
- `supersedes`
- `superseded_by`

Valid statuses:

- `claimed`
- `implementation_started`
- `blocked`
- `waiting_on_user`
- `waiting_on_timer`
- `pr_opened`
- `merged`
- `done`
- `parked`
- `superseded`
- `owner_boundary`

## Path Resolution

The live path is resolved from `scripts.agent_job_registry.resolve_registry_location`
and appends `task-ledger.jsonl`. In this linked worktree it resolves to:

```text
/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl
```

The script does not use a literal worktree `.git/tenn-agent-registry` path.

## Session Trace

The script supports `DATA_MISSING` for `session_id`, `thread_id`,
`codex_goal_id`, and `source_session_ref`. `append --fill-identity` fills only
from explicit safe sources and does not invent IDs.

## Live Ledger Mutation

Live append was not used in this run because the task card does not approve
branch-independent live ledger mutation. The intended ledger entry is preserved
at `handoff/LEDGER_ENTRY.json`.
