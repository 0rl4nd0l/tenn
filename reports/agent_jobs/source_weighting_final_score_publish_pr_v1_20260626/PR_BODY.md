## Summary

Fixes issue #259 by aligning `source_weighting.apply_source_weighting()`
with the documented final-score contract.

Missing explicit credibility now uses the default source weight once as the
resolved credibility dimension. It no longer multiplies by both `source_weight`
and `credibility_weight`, so a default `news_article` at relevance/recency 1.0
scores `0.5` instead of `0.25`.

## Changes

- Compute `final_score` as
  `relevance_score * resolved_credibility * recency_decay`.
- Add focused tests for default `news_article`, `youtube_transcript`, and
  `framework_pdf` scoring.
- Add an explicit credibility override test and an integration-path assertion
  through `apply_weighting_to_chunk()`.
- Include Tenn task/report artifacts for the validated local fix and publish
  lane.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/source_weighting_final_score_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/source_weighting_final_score_publish_pr_v1_20260626.md --repo-root .`

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, source-PDF, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No dependency files changed.
