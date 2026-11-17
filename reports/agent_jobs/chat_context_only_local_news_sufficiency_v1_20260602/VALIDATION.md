# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md` -> exit 0
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .` -> exit 0
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md --repo-root .` -> exit 0
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestChatWithTennTickerPropagation::test_linked_ticker_news_with_different_primary_is_kept_as_context_only -q` -> RED exit 1 before implementation
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py -q` -> exit 0, 48 passed
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py` -> exit 0
- `python3 -m py_compile financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py` -> exit 0
- `git diff --check` -> exit 0

## Runtime Functionality Proof

This task changed backend evidence metadata and tests only. No daemon,
scheduler, ingestion, extraction, DB, or runtime pipeline was started or claimed
working.

| Field | Required evidence |
| --- | --- |
| intended output | Direct chat response metadata for recent/update/news prompts with context-only local-news sources. |
| live output location | `chat_with_tenn()` returned dict; verified through focused unit tests, not a live service. |
| pre-run max timestamp or count | DATA_MISSING; no runtime output baseline was captured because this was not a runtime run. |
| post-run max timestamp or count | DATA_MISSING; no runtime output was produced. |
| rows/files inserted or updated after run start | 0 runtime rows/files; code/report files changed only. |
| readiness/gate status | Focused test gate passed; runtime readiness not evaluated. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_chat_route.py -q` |
| result | DATA_MISSING |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Runtime proof not applicable unless an owner requests live service/API validation. |

result: DATA_MISSING
