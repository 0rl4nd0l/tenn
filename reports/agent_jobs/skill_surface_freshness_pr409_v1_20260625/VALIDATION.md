# Validation

## Preflight

- Portable git guard:
  - exit: 0
  - result: pass, `VALID_TASK_WORKTREE`, `stop_reimplementation=false`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit: 0
  - result: ok, no active jobs
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - exit: 0
  - result: ok

## Post-Patch Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md`
  - exit: 0
  - result: ok
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit: 0
  - result: ok, no active jobs
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - exit: 0
  - result: ok
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
  - exit: 0
  - result: 12 retained repo-backed skill entrypoints
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
  - exit: 0
  - result: no output
- `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: 24 passed, 1 warning
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md --repo-root .`
  - exit: 0
  - result: ok; wrote `reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/diff-check.json`

## Freshness Proof

- Current canonical:
  `b3b3a154590f36e61d297c1ac79fe623526f0b28`
- `SKILLS_SURFACE.md` `last_verified_commit`:
  `b3b3a154590f36e61d297c1ac79fe623526f0b28`
- `SKILLS_SURFACE.md` `last_verified_pr`: `409`
