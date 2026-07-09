# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
  - exit status: 0
  - result: task card valid
- initial red `python3 -m unittest scripts.test_automation_write_gate`
  - wrapper exit status: 0
  - expected test command result: import failed because
    `scripts/automation_write_gate.py` did not exist yet
- `python3 -m unittest scripts.test_automation_write_gate scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
  - exit status: 0
  - result: 23 tests passed
- `python3 scripts/automation_write_gate.py --help`
  - exit status: 0
  - result: CLI help printed
- `python3 scripts/automation_write_gate.py manifest --candidate-json '{"title":"Safe","root_cause":"safe gap","evidence_path":"reports/demo.md","lane":"reporting","risk":"low"}' --dedupe-json '{"status":"new","errors":[]}' --requested-action open_issue --approval-phrase "open issue" --json`
  - exit status: 0
  - result: `status=eligible`, `action=open_issue`, `may_execute=true`
- `python3 scripts/automation_write_gate.py manifest --candidate-json '{"title":"Safe","root_cause":"safe gap","evidence_path":"reports/demo.md","lane":"reporting","risk":"low"}' --dedupe-json '{"status":"maybe","errors":[]}' --requested-action open_issue --approval-phrase "open issue" --json`
  - exit status: 1
  - result: `status=data_missing`, `action=review_only`,
    `may_execute=false`
- `python3 -m py_compile scripts/automation_write_gate.py scripts/test_automation_write_gate.py`
  - exit status: 0
  - result: compile check passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
  - exit status: 0
  - result: changed files are within `allowed_files`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
  - first parallel run exit status: 1
  - first result: `diff-check.json` was checked before the parallel
    `check-diff` command finished writing it
  - rerun exit status: 0
  - rerun result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
  - exit status: 0
  - result: closeout check passed
- `git diff --check`
  - exit status: 0
  - result: no tracked-diff whitespace errors
- code-reviewer pass
  - result: no critical findings, warnings, or suggestions after review fixes
- branch push
  - first attempt: blocked by missing local hook tools `ruff` and `pytest`
  - retry: `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin control-plane/automation-strict-write-gate-layer3-v0-20260709`
  - retry exit status: 0
  - result: branch pushed; pre-push markdown hygiene passed
- draft PR creation
  - method: GitHub connector
  - result: PR #494 opened at
    `https://github.com/0rl4nd0l/tenn/pull/494`

## Pending

- final `git status --short --untracked-files=all`
- PR #494 review and checks
