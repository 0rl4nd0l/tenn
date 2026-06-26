## Summary

Fixes issue #258 by keeping `compute_session_coherence()` inside its documented
`0.0` to `1.0` range.

The scorer previously returned `max(0.0, 1.0 - cosine_similarity)`. Negative
cosine similarity could therefore produce values above `1.0`, even though the
architecture docs and function contract describe `session_coherence` as a
bounded component metric.

## Changes

- Clamp the inverted cosine result to `0.0 <= session_coherence <= 1.0`.
- Add a negative-cosine regression test.
- Stub scorer embedding calls in coherence tests so they do not depend on local
  embedding runtime configuration.
- Include Tenn task/report artifacts for the validated local fix and publish
  lane.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, source-PDF, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No dependency files changed.
