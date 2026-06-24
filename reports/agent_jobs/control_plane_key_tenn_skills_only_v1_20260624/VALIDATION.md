# Validation

## Passed

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-key-tenn-skills-only-v1-20260624 --topic "key Tenn skills only surface" --json`
  - result: pass
  - path ownership: `VALID_TASK_WORKTREE`
  - registry: no active jobs
  - ledger: live and committed sources validated
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md`
  - result: pass
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - result: pass, no active jobs
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: pass, 17 entries checked
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
  - result: exactly 12 retained key/narrative-support skills
- `find .codex/skills -maxdepth 2 -name SKILL.md | sort`
  - result: no visible legacy/custom repo-local skills
- shell-safe active-doc check for legacy `.codex/skills/cockpit-flag-orchestrator/SKILL.md`
  and deleted legacy cockpit support paths
  - result: pass, no active-doc instructions point to the removed legacy skill
- `git diff --check`
  - result: pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md --repo-root .`
  - result: pass
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md --repo-root .`
  - result: pass
- `git status --short --untracked-files=all`
  - result: dirty only with task-card-allowed implementation files and ignored report files before staging
- `git push --dry-run origin HEAD:refs/heads/migration/clean-runtime-baseline-reconstruct-v1`
  - result: blocked by local pre-push hook; missing
    `financial-engine_v2/.venv/bin/ruff` and
    `financial-engine_v2/.venv/bin/pytest`
- `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push origin HEAD:refs/heads/migration/clean-runtime-baseline-reconstruct-v1`
  - result: passed after owner approval; pre-push skipped missing local
    ruff/pytest checks and passed markdown hygiene
  - remote update: `6a777b3d..adabbb79`
- `git rev-parse HEAD origin/migration/clean-runtime-baseline-reconstruct-v1`
  - result: both resolve to `adabbb7945aa00cdec03f3275a7154814200be58`

## Not Run

- Runtime/product/extraction tests were not run because this change only updates
  repo-local skill entrypoints and refreshes control-plane docs.
- Pre-push ruff/pytest checks were bypassed with owner approval because the
  hook-required venv tools are absent in this worktree.
