# Validation

Commands are run from
`/home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626` unless noted
otherwise.

| Command | Result |
| --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626 --topic "issue 260 recency half-life decay" --json` | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; no active jobs |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . search --issue 260` | pass; no matching entries, duplicate classification `UNKNOWN_ASK`; guard duplicate-work classification was `NO_MATCHING_ACTIVE_WORK_FOUND` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...` | pass; claim entry appended |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py::TestSourceWeightingNewsArticle::test_recency_decay_matches_true_half_life_contract financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py::TestSourceWeightingNewsArticle::test_apply_weighting_news_article_one_half_life financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py::TestSourceWeightingNewsArticle::test_apply_weighting_market_commentary_one_half_life` | red pass; failed before source fix with `0.36787944117144233` instead of `0.5` |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass; 29 passed |
| `uv run --with ruff ruff format financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass; initially reformatted four files, then incidental non-source diffs were removed |
| `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass |
| `uv run --with ruff ruff check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass |
| `python3 -m py_compile financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md --repo-root .` | pass; no disallowed files |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md --repo-root .` | pass |
| `gh issue comment 260 --repo 0rl4nd0l/tenn --body ...` | pass; posted `https://github.com/0rl4nd0l/tenn/issues/260#issuecomment-4807424121` |
| `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...` | pass; final `done` entry appended with `owner_boundary=true` |

## Notes

- `uv` warned that it ignored the requirements file `--extra-index-url`; the
  focused tests still installed/resolved the required packages and passed.
- `marketplace_price_intelligence.py` is touched only for a stale source
  comment that described the old time-constant formula.
