# Extraction PR129 CI Test Harness Third Slice

## Summary

- Job: `extraction_pr129_ci_test_harness_third_slice_v1_20260529`
- Related PR: #129
- Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`
- Mode: SAFE EXTENSION, test/report-only
- Lane: Evaluation
- Runtime reload: no
- Canary run: no
- Broad extraction/backfill run: no
- DB/Qdrant/news/memory/canonical truth writes: no
- Source PDF edits/copies/deletes/commits: no
- Parser routing, extraction prompt, schema, model/GPU/service, Cockpit UI, and GitHub issue-state changes: no

## What Changed

This slice fixes the fresh PR #129 GitHub Actions `lint-and-test` failures that were test-harness drift rather than production extraction behavior changes.

- Marketplace benchmark fixtures now use recent `observed_at` timestamps so freshness-dependent tests do not decay as wall-clock time advances.
- News memo signal-routing tests pass explicit `candidate_tickers=["BHP"]`, preserving the current candidate allowlist guard while exercising company/market routing.
- Query-orchestrator coverage now asserts the current speculative-with-announcement behavior when financial rows are missing but announcement/business context is available.
- Cockpit agent/router tests avoid unsupported financial-truth claims in generic router stress coverage and assert the current `api_only` local-blocking and `on_chunk` wrapper behavior.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`
- Selected 15 PR #129 CI failures: `15 passed in 2.93s`
- All touched test files: `217 passed in 31.72s`
- Focused extraction suite: `252 passed, 5 warnings in 3.25s`
- CI-style broad backend+Cockpit suite with backend dev requirements: `2958 passed, 17 skipped, 1 deselected, 57 warnings, 48 subtests passed in 134.69s`
- Targeted Ruff on touched test files: `All checks passed!`
- Targeted `py_compile` on touched test files
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`

Local note: broad backend+Cockpit pytest with the baseline venv stopped during collection on missing local `respx`. The CI-style `uv run --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ...` command includes that dependency and passed.

## Approval And Canary Boundary

The operator approval string for the separate #96 third canary packet has now been supplied:

`APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`

This test-harness job does not execute that canary. The next safe step for canary execution is a separate approval-required runtime task card and immediate pre-run gates from `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json`.

## Files Changed

- `docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md`
- `docs/claude/STATE.md`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_third_slice_v1_20260529/README.md`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_third_slice_v1_20260529/status.json`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_third_slice_v1_20260529/diff-check.json`
- `financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py`
- `financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py`
- `financial-engine_v2/backend/tests/test_marketplace_scanner.py`
- `financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/cockpit/tests/test_agent_stress.py`
- `financial-engine_v2/cockpit/tests/test_cockpit_chat_changes.py`
- `financial-engine_v2/cockpit/tests/test_router_edge_cases.py`

## Files Intentionally Not Touched

- Production extraction/runtime service code.
- DB, Qdrant, news, memory, and canonical financial truth stores.
- Source PDFs and source-data fixtures.
- Parser routing and extraction prompts.
- Runtime/model/GPU/service configuration.
- Cockpit UI.
- Schema and Alembic migrations.
- GitHub issue state.

## Next Safe Step

Commit and push this PR #129 CI harness slice, then recheck PR #129 GitHub Actions. If this branch is green, handle the approved #96 third canary only through a separate runtime task card with fresh registry, queue, GPU, backend health, loaded-code, source-path, and one-document-at-a-time gates.
