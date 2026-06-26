# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue245-marketplace-price-intelligence-route-guard-current-base-v1-20260627 --topic "issue245 marketplace price intelligence route guard" --json`
  - PASS: clean current-base task worktree, canonical head
    `7d6ab6c184332d5413700eb08e6790f530000942`, no matching active work.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627.md`
  - PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627.md --repo-root .`
  - PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627.md --repo-root .`
  - PASS.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - PASS before source edits.
- `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...`
  - PASS for `claimed` entry.

## RED

```bash
uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py -k "standalone_api or price_intelligence_auth"
```

Result before source fix: FAIL as expected.

- 14 failed.
- 2 passed.
- 20 deselected.
- 1 warning: existing pytest config warning for
  `asyncio_default_fixture_loop_scope`.

## GREEN

```bash
uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py -k "standalone_api or price_intelligence_auth"
```

Result after source fix: PASS.

- 16 passed.
- 20 deselected.
- 1 warning: existing pytest config warning for
  `asyncio_default_fixture_loop_scope`.

## Static Checks

```bash
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py
```

Result: PASS, `All checks passed!`.

```bash
python3 -m py_compile financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

## Not Run

- Live backend/Cockpit runtime smoke: not run; task forbids service starts and
  production data mutation.
- Frontend Vitest: not run; no frontend files changed and current source
  evidence shows BFF routes already forward request headers.
