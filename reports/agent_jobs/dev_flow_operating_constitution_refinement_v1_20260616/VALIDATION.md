# Validation

State: local validation passed

Completed checks:

- Task-card validate.
  - Command:
    `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_operating_constitution_refinement_v1_20260616.md`
  - Exit: 0
  - Result: `ok: true`.
- Registry list-active read-only.
  - Command:
    `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Exit: 0
  - Result: `ok: true`, `read_only: true`, `lock_acquired: false`.
- Parse/check changed `SKILL.md` files.
  - Exit: 0
  - Result: parsed 8 changed skills.
- Validate changed JSON templates.
  - Command: `python3 -m json.tool docs/dev_flow/templates/BOARD_DECISION.json`
  - Exit: 0
- `git diff --check`.
  - Exit: 0
- Changed-path guard.
  - Exit: 0
  - Result before report staging: 14 visible changed paths, all allowlisted.
  - Final staged result: 20 staged paths, all exactly allowlisted.
- Product/runtime/data/extraction guard.
  - Exit: 0
  - Result: no blocked product/runtime/data/extraction paths changed.
- Host-global mutation guard.
  - Result: all changed paths are repo-relative allowlisted paths.
- Count-24 guard.
  - Result: no changed path contains `count-24` or `count_24`.
- Final status.
  - Final pre-commit status: 20 staged allowlisted files and no unstaged or
    untracked generated artifacts.

## Notes

- `reports/` is ignored and will be staged with `git add -f`.
- `PYTHONDONTWRITEBYTECODE=1` was used for validation commands where possible.
  A generated `scripts/__pycache__/agent_job_contract...` cache file appeared
  after one validation run and was removed before staging.
