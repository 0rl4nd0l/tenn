# Validation

## Passed

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
```

Result: PASS.

```text
python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
```

Result: PASS; registry claim active for this task.

```text
uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: 8 passed, 1 existing warning.

```text
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: PASS.

```text
python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
```

Result: PASS.

```text
git diff --check
```

Result: PASS.

```text
python3 scripts/agent_job_contract.py check-diff --repo-root . docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
```

Result: PASS.

```text
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
```

Result: PASS.

```text
python3 scripts/agent_task_ledger.py validate
```

Result: PASS.

```text
gh pr view 433 --json number,url,state,isDraft,headRefName,baseRefName,mergeStateStatus,statusCheckRollup,updatedAt
```

Result: PR #433 open, non-draft, `mergeStateStatus=UNSTABLE`; `scan` and
`lint-and-test` were IN_PROGRESS at `2026-06-26T19:08:58Z`.

## Known Validation Gaps

- No live backend/Cockpit runtime was started.
- No live or production TradingView alert store was queried.
- The prior local #246 work was not pushed directly because it is dirty,
  unpublished, and based on older canonical; this current-base branch adopts the
  same small fix on `7d6ab6c184332d5413700eb08e6790f530000942`.
