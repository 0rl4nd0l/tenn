# Commands - Agent Flow Cleanup Execution 2026-06-16

## Preflight

```bash
pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all
python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md
python3 scripts/agent_job_registry.py list-active --read-only
```

Result:

- repo: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- branch: `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609`
- HEAD: `9dfa0f83cc09bf2e9edf40f659e0e2fdce0fa374`
- task card validated
- registry read-only check passed with `active_jobs=[]` and `lock_acquired=false`

## Focused Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/agent_job_hook.py scripts/check_agent_hooks.py scripts/agent_job_contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m json.tool .claude/settings.json >/tmp/claude_settings_check.json
bash -n scripts/sync_codex_skills.sh
PYTHONDONTWRITEBYTECODE=1 financial-engine_v2/.venv/bin/pytest -q -p no:cacheprovider scripts/test_agent_job_hook.py scripts/test_check_agent_hooks.py scripts/test_agent_job_contract.py
```

Result:

- syntax checks passed
- JSON parse passed
- shell syntax passed
- focused tests: `51 passed`

## Diagnostic Commands

```bash
bash scripts/sync_codex_skills.sh
python3 scripts/check_agent_hooks.py --repo-root .
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md --repo-root .
```

Results:

- skill sync was dry-run only: `linked=0`, `would_link=6`, `skipped=0`
- hook checker returned exit `0` with `"ok": false` because Git hooks are
  missing at the effective configured path
- report-artifact check initially failed before this bundle existed, proving the
  checker catches missing artifacts

## Stale Reference Scan

```bash
rg -n "TODO|FIXME|/home/l4nd0/tenn|/workspace|Never end.*uncommitted|never end.*uncommitted|All agents MUST|ALL AGENTS|list-active --read-only is missing|PostToolUse ruff|Stop diff summary|Codex ported|full_history_ticker_sync.py.*Runs|\\.codex/skills.*repo-local" ...
```

Remaining hits were intentional:

- `AGENTS.md` warning not to assume `/workspace`
- legacy/custom `.codex/skills` labels
- historical source path in `docs/claude/gap-analysis.md`

## Final Validation

Recorded after report completion:

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md
python3 scripts/agent_job_registry.py list-active --read-only
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/agent_job_hook.py scripts/check_agent_hooks.py scripts/agent_job_contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m json.tool .claude/settings.json >/tmp/claude_settings_final.json
bash -n scripts/sync_codex_skills.sh
PYTHONDONTWRITEBYTECODE=1 financial-engine_v2/.venv/bin/pytest -q -p no:cacheprovider scripts/test_agent_job_hook.py scripts/test_check_agent_hooks.py scripts/test_agent_job_contract.py
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md --repo-root .
git diff --check
git status --short --untracked-files=all
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md --repo-root . --no-write-report
```

## Final Package Staging

```bash
git add -- <approved agent-flow and .githooks package files>
git add -f -- reports/agent_jobs/agent_flow_cleanup_execution_v1_20260616/... reports/agent_jobs/git_hook_install_execution_v1_20260616/...
git diff --cached --name-only
git diff --cached --check
git status --short --untracked-files=all
```
