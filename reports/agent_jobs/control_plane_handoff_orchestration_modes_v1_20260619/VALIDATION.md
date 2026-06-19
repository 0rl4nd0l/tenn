# Validation

Status: passed

## Required Checks

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`: exit 0
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: exit 0
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, no active jobs
- Skill frontmatter/description check: exit 0
- Visible skill count check: exit 0, count stayed 10
- Active removed-entrypoint reference check: exit 0, removed entrypoints absent
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md --repo-root .`: exit 0
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md --repo-root .`: exit 0
- `git diff --check`: exit 0
- Forbidden product/runtime/data/extraction/count-24 path guard: exit 0
- Host-global guard: exit 0
- JSON checks for `BOARD_DECISION.json`, `git_guard.json`, and
  `ledger_entry.json`: exit 0
- `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py`: exit 0
- `python3 -m unittest tests.test_opencode_worker_bridge`: exit 0, 21 tests

## Evidence Notes

- Task ledger validation saw 12 live entries and 0 committed entries after the
  PR-review follow-up entry.
- Read-only registry returned `active_jobs: []`.
- Check-diff wrote `diff-check.json` and reported no disallowed files.
- Check-report-artifacts found every allowed report artifact present and
  non-empty.
- Product/runtime/data/extraction/count-24 guard inspected the git diff and
  untracked non-ignored paths; only control-plane docs, skills, templates, and
  task-card/test/bridge/report paths were present.
- Host-global guard inspected changed repo paths for absolute or out-of-repo
  host-global paths; none were present.
