## Summary

Fixes issue #261 from current canonical by isolating malformed chat source
`published_at` values during source weighting.

This supersedes conflicted PR #419, which was based before PRs #416 and #418
landed.

## Changes

- Catch malformed `published_at` parse failures inside
  `apply_weighting_to_chunk()`.
- Apply neutral `recency_decay = 1.0` for malformed timestamps.
- Preserve visible metadata:
  `recency_status=malformed_published_at`,
  `recency_warning=invalid_published_at`, and `published_at_parse_error`.
- Add regression coverage for direct source weighting and chat strategy keeping
  a valid neighboring chunk.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q` => 36 passed.
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q` => 34 passed.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` => passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` => passed.
- `git diff --check` => passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md --repo-root .` => passed.
