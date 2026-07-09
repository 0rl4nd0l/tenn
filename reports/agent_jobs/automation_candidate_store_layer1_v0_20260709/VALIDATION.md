# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
  - exit status: 0
  - result: task card valid
- first `python3 -m unittest scripts.test_automation_candidate_store scripts.test_system_brief`
  - exit status: 1
  - result: `datetime.UTC` is unavailable on Python 3.10.12
  - fix: changed helper/tests to `timezone.utc`
- `python3 -m unittest scripts.test_automation_candidate_store scripts.test_system_brief`
  - exit status: 0
  - result: 13 tests passed
- `python3 scripts/automation_candidate_store.py --help`
  - exit status: 0
  - result: CLI help printed
- `python3 scripts/automation_candidate_store.py fingerprint --job demo --lane reporting --evidence-path reports/demo.md --root-cause 'demo'`
  - exit status: 0
  - result: `cand_v1_cfd0a351b601be7bced59702`
- `python3 scripts/system_brief.py --repo-root /home/l4nd0/tenn-automation-candidate-store-layer1-v0-20260709 --automation-root /home/l4nd0/.codex/automations/tenn --json`
  - exit status: 0
  - JSON parse status: 0
- code-reviewer pass
  - result: no critical findings, warnings, or suggestions after fail-soft read
    fix

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
  - exit status: 0
  - result: changed files are within `allowed_files`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
  - exit status: 0
  - result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
  - exit status: 0
  - result: closeout check passed

- `git diff --check`
  - exit status: 0
  - result: no tracked-diff whitespace errors
- `rg -n '[[:blank:]]$' docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md scripts/automation_candidate_store.py scripts/test_automation_candidate_store.py scripts/system_brief.py scripts/test_system_brief.py reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/README.md reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/STATE.md reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/VALIDATION.md`
  - exit status: 1 expected when wrapped with shell inversion, wrapper exit
    status: 0
  - result: no trailing whitespace in changed files or report artifacts

## Publish Closeout

- local commit: `45e71d9a Add automation candidate store layer`
- branch push:
  - used `TENN_ALLOW_MISSING_HOOK_TOOLS=1` because local
    `financial-engine_v2/.venv` lacks `ruff` and `pytest`
  - remote branch:
    `origin/control-plane/automation-candidate-store-layer1-v0-20260709`
- draft PR: #492 `Add automation candidate store layer`
  - URL: `https://github.com/0rl4nd0l/tenn/pull/492`
