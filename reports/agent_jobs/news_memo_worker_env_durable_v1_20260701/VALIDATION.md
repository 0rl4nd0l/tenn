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
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .` | 0 | PASS in the code-only pass; final live-proof artifact check is rerun below. |
| Final code review | 0 | PASS_WITH_FIX: narrowed compose host-path alias from full NVMe data root to only `data/reports/research_memory`. |
| Redis/memo baseline capture to `queue_before.json` and `memo_before.json` | 0 | PASS: `llm_gpu=0`, parked stale queue depth 42, memo file 411 valid JSON lines, sha256 `3bea3a55979ec5fbfff4dcf69be467041a631c8e80ac834cfd0746beca5cc519`. |
| LLM endpoint probe to `llm_models.json` | 0 | PASS: `http://127.0.0.1:8001/v1/models` returned HTTP 200 and listed loaded `model:qwen2.5-14b-instruct`; Ollama `/api/tags` returned HTTP 200. |
| Candidate preview to `candidate_preview.json` | 0 | PASS: selected current missing source `news:art_78563f510fe7a2e3c622a9ef`, published `2026-07-01T06:46:35Z`. |
| Temporary worker start: `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/celery -A app.celery_app.celery worker --loglevel=INFO --concurrency=1 --pool=solo -Q llm_gpu -n memo-proof-20260701T2034@%h` | 0 | PASS: worker ready on broker `redis://127.0.0.1:6379/0`, results `redis://127.0.0.1:6379/1`, queue `llm_gpu`. |
| `scripts/backfill_missing_news_memos.py --db-path /mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news_articles.sqlite --since-hours 0 --limit 1 --memo-diagnostics-path /mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/news_memos.jsonl --wait-for-memos --memo-wait-timeout-seconds 240 --memo-wait-poll-interval-seconds 2 --dispatch-batch-size 1 --memo-llm-url http://127.0.0.1:8001 --memo-llm-model model:qwen2.5-14b-instruct --summary-json reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/postfix_live_backfill_summary.json` | 0 | PASS: `status=complete`, `dispatched=1`, `tasks_observed=1`, `tasks_completed=1`, `tasks_failed=0`, `tasks_pending=0`, `tasks_unobserved=0`. |
| Post-run proof capture to `queue_after.json`, `memo_after.json`, and `runtime_proof_live.json` | 0 | PASS: memo file 412 valid JSON lines, sha changed to `575ab19d726ac12e76f1b1654e5c4910151f70d7cf4ffa8f0282ad2c2fdf9499`, proof source present with `llm_url=http://127.0.0.1:8001` and `llm_model=model:qwen2.5-14b-instruct`; parked queue stayed depth 42. |
| Worker shutdown check: `tail worker.log` and `pgrep -af 'memo-proof-20260701T2034|celery.*llm_gpu'` | 0 | PASS: worker warm-shut down; no matching worker remained. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md` | 0 | PASS after adding exact live-proof report artifacts to the task-card allowlist. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .` | 0 | PASS: no disallowed tracked changes. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .` | 0 | PASS: all live-proof artifacts exist. |
| `git diff --check` | 0 | PASS after report/proof updates. |
| JSON validity check for proof artifacts | 0 | PASS: 10 JSON files parsed. |
| `python3 scripts/tenn_dev_status.py` | 0 | INFO: reported intentional related dirty state before commit; `check-diff` and task-card validation covered the dirty file set. |
