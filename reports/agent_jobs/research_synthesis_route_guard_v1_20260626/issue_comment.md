Local fix prepared for issue #244 on branch `safe/issue244-research-synthesis-route-guard-v1-20260626` in worktree:

`/home/l4nd0/tenn-issue244-research-synthesis-route-guard-v1-20260626`

What changed:

- `POST /research/synthesize` now registers `require_api_key`, so it rejects missing/wrong keys when `settings.local_api_key` is configured.
- Missing or invalid key requests now fail before `synthesize_research()` runs.
- Matching-key requests still reach synthesis.
- `docs/architecture/19_backend_api_surface.md` now documents the route as an authenticated server-side inference path.

Validation:

- RED before fix: focused route-auth test failed as expected, 3 failures / 1 pass.
- GREEN after fix: `test_research_route_auth.py` passed, 4 tests.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py` passed.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md --repo-root .` passed.
- `git diff --check` passed.

Report artifacts:

`reports/agent_jobs/research_synthesis_route_guard_v1_20260626/`

I am leaving the issue open because the fix is local/unpublished. No DB, Qdrant, Redis, news, memory, extraction, source document, runtime, service, model, GPU, lockfile, dependency install, merge/rebase/reset/stash/clean, or issue-close mutation was performed.
