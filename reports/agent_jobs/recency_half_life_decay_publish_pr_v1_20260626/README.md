# Recency Half-Life Decay Publish PR

Status: validated; draft PR pending

## Summary

This lane publishes the validated local issue #260 fix as a draft PR. It does
not merge the PR or close the issue.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626`
- Branch: `safe/issue260-recency-half-life-decay-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Validation

Focused validation passed:

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  returned `29 passed`.
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  passed.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  passed.
- `git diff --check` passed.

## Runtime Functionality Proof

This publish lane does not claim live runtime/service functionality. It
publishes a helper/test fix for documented recency half-life semantics.

| Field | Required evidence |
| --- | --- |
| intended output | `compute_recency_decay()` returns true half-life decay: one `half_life_days` interval returns `0.5`, two intervals return `0.25`. |
| live output location | Source helper `financial-engine_v2/backend/app/services/commentary_decay.py`; focused tests in `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`; no live runtime output claimed. |
| pre-run max timestamp or count | `DATA_MISSING`; no live runtime baseline captured because this is a no-runtime helper publish. |
| post-run max timestamp or count | `DATA_MISSING`; no live runtime output checked. |
| rows/files inserted or updated after run start | Source/test files plus task/report artifacts committed in the draft PR branch. |
| readiness/gate status | Focused source-weighting tests, ruff format/check, py_compile, and `git diff --check` passed. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`; `uv run --with ruff ruff format --check ...`; `uv run --with ruff ruff check ...`; `python3 -m py_compile ...`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Draft PR must be opened, reviewed, and merged before issue #260 can close. |

result: PARTIAL

## PR

Pending.
