# Commands - Git Hook Install Execution

```bash
pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all
sed -n '1,240p' .agents/skills/tenn-task-card-registry-safety/SKILL.md
sed -n '1,240p' docs/agent_tasks/git_hook_install_plan_v1_20260616.md
sed -n '1,260p' scripts/check_agent_hooks.py
sed -n '1,260p' scripts/test_check_agent_hooks.py
python3 scripts/agent_job_registry.py list-active --read-only
mkdir -p .githooks reports/agent_jobs/git_hook_install_execution_v1_20260616
python3 scripts/agent_job_contract.py validate docs/agent_tasks/git_hook_install_execution_v1_20260616.md
chmod +x .githooks/pre-commit .githooks/pre-push
git config core.hooksPath .githooks
git config --show-origin --get-all core.hooksPath
git config --local core.hooksPath /home/l4nd0/tenn/.git/hooks
git config --worktree core.hooksPath .githooks
git config --show-origin --get-all core.hooksPath
python3 scripts/check_agent_hooks.py --repo-root . --strict --expect-fingerprint 'pre-commit=git rev-parse --show-toplevel' --expect-fingerprint 'pre-push=git rev-parse --show-toplevel'
financial-engine_v2/.venv/bin/pytest -q scripts/test_check_agent_hooks.py
python3 scripts/agent_job_registry.py list-active --read-only
git config --show-origin --get core.hooksPath
git rev-parse --git-path hooks
git diff --check
python3 -m py_compile scripts/check_agent_hooks.py
git status --short --untracked-files=all
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/git_hook_install_execution_v1_20260616.md --repo-root . --no-write-report
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/git_hook_install_execution_v1_20260616.md --repo-root .
.githooks/pre-push
.githooks/pre-commit
GIT_DIR="$(git rev-parse --git-dir)" GIT_PREFIX= .githooks/pre-push
GIT_DIR="$(git rev-parse --git-dir)" GIT_PREFIX= .githooks/pre-commit
```
