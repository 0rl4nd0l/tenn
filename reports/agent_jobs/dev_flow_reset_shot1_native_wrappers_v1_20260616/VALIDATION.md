# Validation

State: local validation passed

## Completed Checks

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_reset_shot1_native_wrappers_v1_20260616.md`
  - Exit: 0
  - Result: `ok: true`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Exit: 0
  - Result: `ok: true`, `read_only: true`, `lock_acquired: false`,
    `active_jobs: []`
- Parse/check every new `SKILL.md`
  - Exit: 0
  - Result: parsed 8 skills with required frontmatter.
- Verify required wrapper skills exist
  - Exit: 0
  - Result: 8 required wrapper skills present.
- Verify required template docs exist
  - Exit: 0
  - Result: 10 required templates present.
- `python3 -m json.tool docs/dev_flow/templates/BOARD_DECISION.json`
  - Exit: 0
- `git diff --check`
  - Exit: 0
- Initial task-card `check-diff`
  - Command:
    `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_reset_shot1_native_wrappers_v1_20260616.md --no-write-report`
  - Exit: 0
  - Result: `ok: true`

## Final Staged Guards

- Staged task-card `check-diff`
  - Command:
    `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_reset_shot1_native_wrappers_v1_20260616.md --no-write-report`
  - Exit: 0
  - Result: 26 staged files, `ok: true`, `disallowed_files: []`.
- `git diff --cached --check`
  - Exit: 0
- Changed-path guard
  - Exit: 0
  - Result: 26 staged paths exactly match the task-card `allowed_files`.
- Product/runtime/data/extraction path guard
  - Exit: 0
  - Result: no blocked product/runtime/data/extraction paths changed.
- Host-global mutation guard
  - Result: staged paths are all repo-relative allowlisted paths; no
    host-global files were touched.
- GitHub mutation guard before PR creation
  - Result: no `gh` mutation commands were run before local validation passed.

## Notes

- `.agents/` is ignored by `.gitignore`; new wrapper skills require
  `git add -f`.
- `reports/` is ignored by `.git/info/exclude`; report artifacts require
  `git add -f`.
- A Python validation run created `scripts/__pycache__/agent_job_contract...`;
  that exact generated cache file was removed before staging.
