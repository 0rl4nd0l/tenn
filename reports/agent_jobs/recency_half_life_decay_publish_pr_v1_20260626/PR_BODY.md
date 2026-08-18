## Summary

Fixes issue #260 by making `compute_recency_decay()` implement true
`half_life_days` semantics.

The helper previously used `exp(-age / half_life)`, which treats
`half_life_days` as a time constant rather than a half-life. One configured
half-life interval returned about `0.367879` instead of `0.5`.

## Changes

- Use `exp(-ln(2) * age / half_life)` for centralized recency decay.
- Add fixed-timestamp tests proving one half-life decays to `0.5` and two
  half-lives decay to `0.25`.
- Add source-weighting coverage for `news_article` and `market_commentary`.
- Update the stale marketplace source comment that described the old formula.
- Include Tenn task/report artifacts for the validated local fix and publish
  lane.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, source-PDF, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No dependency files changed.
