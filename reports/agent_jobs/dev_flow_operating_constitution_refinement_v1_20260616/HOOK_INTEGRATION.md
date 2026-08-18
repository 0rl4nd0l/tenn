# Hook Integration

This run documents hook cooperation only. It does not edit host-global Codex
files, repo hook scripts, or hook configuration.

Existing backend guards to recognize:

- Host `goal_optimizer_pre_tool.py`: warns on high token/output burn.
- Host `stop_check.py`: warns about terminal dirty state.
- Repo `scripts/agent_job_hook.py`: enforces task-card, registry, and diff
  contract checks from repo hook surfaces.

Workflow commands should preflight task-card, registry, branch, diff, and dirty
state before hooks fire. Hooks remain backstops, not the main workflow brain.
