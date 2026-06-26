# Validation

Commands are run from
`/home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626` unless noted
otherwise.

| Command | Result |
| --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626 --topic "issue 261 malformed source date isolation" --json` | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; no active jobs |
| `python3 scripts/agent_task_ledger.py --repo-root . search --issue 261` | pass; no matching entries, duplicate classification `UNKNOWN_ASK`; guard duplicate-work classification was `NO_MATCHING_ACTIVE_WORK_FOUND` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md` | pass |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py::TestSourceWeightingNewsArticle::test_apply_weighting_malformed_published_at_uses_neutral_recency_with_warning financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py::TestRetrieveChatContext::test_apply_chat_strategy_keeps_valid_neighbor_with_malformed_date` before source fix | expected fail; `ValueError: invalid literal for int() with base 10: b'not-'` from `dateutil.parser.isoparse("not-a-date")` |
| Same focused malformed-date test command after source fix | pass; 2 passed |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass; 28 passed |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_news_retrieval_eval.py` | pass; 34 passed |
| `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass |
| `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass |
| `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | fail; selected files would be reformatted. Full formatter output was not retained because it included unrelated legacy formatting churn outside the minimum necessary fix. |
| `python3 -m json.tool reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/status.json` | pass |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md` | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md --repo-root .` | pass |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md --repo-root .` | pass |
| `gh issue view 261 --repo 0rl4nd0l/tenn --json number,state,title,comments,url` | pass; issue open, no comments before this lane's comment |
| `gh issue comment 261 --repo 0rl4nd0l/tenn --body ...` | pass; `https://github.com/0rl4nd0l/tenn/issues/261#issuecomment-4807663121` |
