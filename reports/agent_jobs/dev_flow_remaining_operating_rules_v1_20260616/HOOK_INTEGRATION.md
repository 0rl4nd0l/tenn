# Hook Integration

The existing host and repo hooks remain backend guards and are not reimplemented.

- `goal_optimizer_pre_tool.py`: token and broad-output warning guard.
- `stop_check.py`: terminal dirty-warning suppression guard.
- `scripts/agent_job_hook.py`: repo task-card, registry, and diff contract guard.
