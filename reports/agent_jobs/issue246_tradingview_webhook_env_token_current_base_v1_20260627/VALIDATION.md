# Validation

## Passed

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md
```

Result: `PASS`

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: `PASS`, 10 passed.

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/core/config.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: `PASS`

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

## Pending

- PR publication/checks/review are pending.
- No live backend/browser smoke was run; runtime proof is `PARTIAL`.
