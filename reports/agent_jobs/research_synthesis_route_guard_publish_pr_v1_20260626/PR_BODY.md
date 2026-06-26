## Summary

Fixes issue #244 by requiring the existing local API-key guard on
`POST /research/synthesize`.

The route performs server-side research synthesis, so configured-key mode should
reject missing or wrong `X-API-Key` values before invoking
`synthesize_research()`.

## Changes

- Add `Depends(require_api_key)` to the research synthesis route.
- Add focused route-auth tests proving dependency registration, missing/wrong
  key rejection before synthesis, and matching-key success.
- Document the route authentication contract in the backend API surface doc.
- Include Tenn task/report artifacts for the validated local fix and publish
  lane.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, source-PDF, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No dependency files changed.
