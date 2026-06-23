# Validation

## Control-Plane Guard Preservation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md`
  - Result: PASS.
- `python3 -m py_compile .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
  - Result: PASS.
- `python3 -m unittest discover -s .agents/skills/tenn-git-guard/tests`
  - Result: PASS, `Ran 5 tests`.
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "tenn git guard global runner preservation" --json`
  - Result: PASS, saved to `GUARD_SMOKE.json`.
  - Key fields: `guard_support_status=PASS`, `registry_status=PASS`, `ledger_status=PASS`, `final_decision=pass`.

## Greyhound Runtime Validation

- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound-runtime-master-live-20260621 --topic "score-live output guard" --json`
  - Result: WARNING, saved to `RUNTIME_GUARD_SMOKE.json`.
  - Key fields: `guard_support_status=PASS`, `registry_status=PASS`, `ledger_status=DATA_MISSING`, `data_missing_sources=["ledger:committed", "ledger:live"]`.

## Review

Code-reviewer stance was applied to the guard runner, tests, skill instructions,
and skill-surface update. No critical findings, warnings, or suggestions were
identified in the guard preservation changes.

## Closeout Checks

- `git diff --check`
  - Result: PASS.
- `git diff --cached --check`
  - Result: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md --no-write-report`
  - Result: PASS.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md --repo-root .`
  - Result: PASS.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md --repo-root .`
  - Result: PASS.
