# Summary

- Fixes direct `chat_with_tenn()` evidence metadata for issue #265.
- Adds `insufficient_for_recent_news` when a recent/update/news prompt only has
  context-only local news and no claim-verified local-news source.
- Adds regression coverage for direct chat and `/chat` route envelope
  preservation.

# Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py`
- `git diff --check`

# Safety

No runtime starts, service changes, DB/Qdrant/news/memory writes, prompt
changes, source PDF changes, or gold-label changes were performed.

# Branch State

This branch was refreshed onto
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`55da116ad6b20adccb7a66931601895b3e8ab757` before PR creation.
