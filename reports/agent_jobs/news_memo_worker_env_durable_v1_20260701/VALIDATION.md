# Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-news-memo-worker-env-durable-v1-20260701 --topic news_memo_worker_env_durable_v1_20260701 --json` | 0 | PASS: `VALID_TASK_WORKTREE`, `stop_reimplementation=false`, no active duplicate work. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md` | 0 | PASS after correcting primary lane to `Memory`. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | PASS: no active jobs. |
| `python3 -m py_compile scripts/load_news_to_qdrant.py scripts/backfill_missing_news_memos.py scripts/test_nightly_news_runtime_guard.py scripts/test_load_news_qdrant_preflight.py scripts/test_backfill_missing_news_memos.py` | 0 | PASS. |
| `bash -n financial-engine_v2/scripts/nightly_news.sh` | 0 | PASS. |
| `python3 -m unittest scripts.test_nightly_news_runtime_guard` | 0 | PASS: 6 tests. |
| `python3 -m pytest scripts/test_load_news_qdrant_preflight.py scripts/test_backfill_missing_news_memos.py -q` | 1 | Environment gap: system Python has no `pytest`. |
| `python3 -m unittest scripts.test_load_news_qdrant_preflight scripts.test_backfill_missing_news_memos` | 1 | Environment gap: missing `qdrant_client` and `pydantic_settings`; this command also exposed fixture expectations updated for current market eligibility. |
| `uv run --with pytest --with qdrant-client --with pydantic-settings python -m pytest scripts/test_load_news_qdrant_preflight.py scripts/test_backfill_missing_news_memos.py -q` | 0 | PASS: 33 tests, 1 existing pytest config warning for `asyncio_default_fixture_loop_scope`. |
| `python3 -c "import yaml; yaml.safe_load(open('financial-engine_v2/docker-compose.yml')); print('yaml ok')"` | 0 | PASS. |
| `docker compose -f financial-engine_v2/docker-compose.yml config --quiet` | 1 | Environment gap: `.env.docker` is absent in this worktree. |
| `bash -o pipefail -c 'python3 - <<"PY" ... PY'` | 0 | PASS: compose config validates when service `env_file` entries are removed for parse-only validation. |
| `git diff --check` | 0 | PASS. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .` | 0 | PASS: no disallowed files. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .` | 0 | PASS after adding exact report artifacts and `result: DATA_MISSING` runtime-proof line. |
| Final code review | 0 | PASS_WITH_FIX: narrowed compose host-path alias from full NVMe data root to only `data/reports/research_memory`. |
