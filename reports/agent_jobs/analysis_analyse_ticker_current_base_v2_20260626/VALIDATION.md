# Validation

| Command | Status | Notes |
| --- | --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue253-analyse-ticker-current-base-v2-20260626 --topic "issue 253 analyse ticker current base repair" --json` | `PASS_PRE_EDIT`; `DIRTY_RELATED_WORKTREE_POST_EDIT` | Pre-edit current-base worktree accepted. Post-edit guard blocks because intended task files are dirty before commit. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md` | `PASS` | Task card valid. |
| `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/analysis_analyse_ticker_current_base_v2_20260626.md --repo-root .` | `PASS` | Only this active claim overlaps. |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | `PASS` | Live and committed ledgers validate. |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_analysis_modules.py -q` | `PASS` | 49 passed in 1.26s. |
| `uv run --with ruff ruff check financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` | `PASS` | All checks passed. |
| `python3 -m py_compile financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` | `PASS` | No output. |
| `git diff --check` | `PASS` | No output. |
| `uv run --with ruff ruff format --check financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` | `FAILED_NON_GATE` | Would reformat both files due pre-existing whole-file style. Formatter churn was intentionally removed to keep the bug fix minimal. |
| code review | `PASS` | No critical, warning, or suggestion findings. |
| GitHub checks | `PENDING` | Not yet run. |
