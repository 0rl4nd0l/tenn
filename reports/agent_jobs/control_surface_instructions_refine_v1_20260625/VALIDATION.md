# Validation

## Red Checks

- `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py`
  - exit: 1
  - result: expected RED
  - finding: `tests/test_agent_task_ledger.py` expected
    `## Next 10 milestones`, while `docs/dev_flow/templates/HANDOFF.md` used
    `## Next 5-10 key milestones`.
- `find .codex/skills -maxdepth 2 -name SKILL.md | sort`
  - exit: 1
  - result: expected RED
  - finding: `.codex/skills` is absent in current canonical, so instructions
    must use an absent-directory-safe check.

## Post-Fix Validation

- `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: 24 passed, 1 warning
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
  - exit: 0
  - result: no output; `.codex/skills` absent
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
  - exit: 0
  - result: 12 retained repo-backed skill entrypoints
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md`
  - exit: 0
  - result: ok
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit: 0
  - result: ok, no active jobs
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - exit: 0
  - result: ok, live and committed ledgers checked
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md --repo-root .`
  - exit: 0
  - result: ok; wrote `reports/agent_jobs/control_surface_instructions_refine_v1_20260625/diff-check.json`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md --repo-root .`
  - exit: 0
  - result: ok
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md --repo-root .`
  - exit: 0
  - result: ok

## Final Ledger Append

- `python3 scripts/agent_task_ledger.py append --fill-identity --entry-json <control_surface_instructions_refine_v1_20260625>`
  - exit: 0
  - result: ok
  - path:
    `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`

## Final Rerun

- Final validation rerun after report closeout text update: passed.
