# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
  - exit status: 0
  - result: task card valid
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit status: 0
  - result: no active jobs
- initial red `python3 -m unittest scripts.test_automation_write_executor_plan`
  - exit status: 1
  - expected result: import failed because
    `scripts/test_automation_write_executor_plan.py` did not exist yet
- first green attempt:
  `python3 -m unittest scripts.test_automation_write_executor_plan scripts.test_automation_write_gate scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
  - exit status: 1
  - result: planner blocked an int PR number from the manifest
- green rerun:
  `python3 -m unittest scripts.test_automation_write_executor_plan scripts.test_automation_write_gate scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
  - exit status: 0
  - result: 32 tests passed
- `python3 scripts/automation_write_executor_plan.py --help`
  - exit status: 0
  - result: CLI help printed
- `python3 scripts/automation_write_executor_plan.py plan --manifest-json '{"read_only":true,"status":"eligible","may_execute":true,"action":{"type":"open_issue","target":{"title":"Safe","body_source":"reports/demo.md","lane":"reporting","risk":"low","root_cause":"safe gap"}}}' --json`
  - exit status: 0
  - result: `status=planned`, `action=open_issue`, `execute=false`
- `python3 -m py_compile scripts/automation_write_executor_plan.py scripts/test_automation_write_executor_plan.py`
  - exit status: 0
  - result: compile check passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
  - exit status: 0
  - result: changed files are within `allowed_files`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
  - exit status: 0
  - result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
  - exit status: 0
  - result: closeout check passed
- `git diff --check`
  - exit status: 0
  - result: no tracked-diff whitespace errors
- `rg -n "sk-|api[_-]?key|secret|token|password" scripts/automation_write_executor_plan.py scripts/test_automation_write_executor_plan.py docs/agent_tasks/automation_write_executor_plan_layer4_v0_20260709.md`
  - exit status: 0
  - result: no secret material; only the safety-boundary word `secret` and a
    test worktree path matched
- `rg -n "subprocess|os\\.system|Popen|run\\(" scripts/automation_write_executor_plan.py`
  - exit status: 1
  - result: no subprocess or shell execution surface in the helper
- code-reviewer pass
  - result: no critical findings, warnings, or suggestions after cleanup
- branch push
  - first attempt: blocked by missing local hook tools `ruff` and `pytest`
  - retry:
    `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin control-plane/automation-write-executor-plan-layer4-v0-20260709`
  - retry exit status: 0
  - result: branch pushed; pre-push markdown hygiene passed
- draft PR creation
  - method: GitHub connector
  - result: PR #495 opened at
    `https://github.com/0rl4nd0l/tenn/pull/495`

## Pending

- final `git status --short --untracked-files=all`
- PR #495 review and checks
