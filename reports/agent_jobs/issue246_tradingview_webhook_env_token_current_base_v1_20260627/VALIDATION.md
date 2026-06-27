# Validation

## Passed

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md
```

Result: `PASS`

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: `PASS`, 12 passed after PR #449 review follow-up.

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/core/config.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: `PASS`

The same focused pytest and ruff commands were rerun after addressing PR #449
automated review feedback about TradingView-sendable tokens. Result: `12
passed` and `All checks passed!`.

The focused pytest and ruff commands were rerun again after addressing PR #449
automated review feedback about process-env leakage in the env-file settings
test. Result: `12 passed` and `All checks passed!`.

```bash
python3 -m py_compile financial-engine_v2/backend/app/core/config.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: `PASS`

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md --repo-root . --no-write-report
```

Result: `PASS`

```bash
git diff --check
```

Result: `PASS`

```bash
python3 scripts/agent_task_ledger.py validate
```

Result: `PASS`

```bash
TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin safe/issue246-tradingview-webhook-env-token-current-base-v1-20260627
```

Result: `PASS`

The local pre-push hook skipped missing repo-venv `ruff`/`pytest` only after
explicit `uv` validation had passed. Markdown hygiene passed.

```bash
gh pr create --repo 0rl4nd0l/tenn --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/issue246-tradingview-webhook-env-token-current-base-v1-20260627
```

Result: `PASS`, opened PR #449.

## Pending

- GitHub checks/review/merge/closeout are pending after the latest PR #449
  review-fix push.
- No live backend/browser smoke was run; runtime proof is `PARTIAL`.
