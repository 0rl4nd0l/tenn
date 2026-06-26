## Summary

Fixes issue #261 by isolating malformed `published_at` values during chat
source weighting.

A malformed timestamp now gets neutral recency and visible metadata instead of
raising from date parsing and degrading the whole chat retrieval bundle.

## Changes

- Catch malformed `published_at` parse failures inside
  `apply_weighting_to_chunk()`.
- Apply neutral `recency_decay = 1.0` for malformed timestamps.
- Preserve visible provenance metadata:
  `recency_status=malformed_published_at`,
  `recency_warning=invalid_published_at`, and `published_at_parse_error`.
- Add focused tests for malformed source weighting and `_apply_chat_strategy()`
  retaining a valid neighboring chunk.
- Include Tenn task/report artifacts for the validated local fix and publish
  lane.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_recency_malformed_date_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_recency_malformed_date_publish_pr_v1_20260626.md --repo-root .`

## Integration Note

This PR is adjacent to open source-weighting PRs #416 and #418. It is published
as draft so integration order can be reviewed deliberately before merge.

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, source-PDF, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No dependency files changed.
