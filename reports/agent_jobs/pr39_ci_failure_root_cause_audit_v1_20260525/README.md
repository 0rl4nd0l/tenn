# PR #39 CI Failure Root-Cause Audit

## Scope

- GitHub issue: #66.
- PR: #39, `[codex] integrate trust foundation next phase`.
- Lane: Evaluation.
- Execution mode: AUDIT MODE.
- Target system layer: GitHub Actions status and CI failure reporting only.
- Contract boundary: no code, workflow, dependency, lockfile, runtime, service, or data-store changes.

## Executive Result

The current PR #39 CI failure is in the `CI / lint-and-test` job, step `Pytest (backend + cockpit)`.

Current latest failing run:

- Run: `26379324415`
- Job: `77645418602`
- Head SHA: `9940a9a78bad0694ce9066528a8f40067128eb2f`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Job URL: `https://github.com/0rl4nd0l/tenn/actions/runs/26379324415/job/77645418602`
- Result: `65 failed, 2822 passed, 18 skipped, 1 deselected, 57 warnings, 38 subtests passed`

The failure is not currently caused by package installation or Ruff:

- `Install dependencies`: passed.
- `pip-audit (advisory)`: passed.
- `Ruff`: passed.
- `Pytest (backend + cockpit)`: failed.
- `Pytest (autodev)`: skipped because the previous step failed.
- `Sloppy Scan`: passed on matching head SHA.

## Failure Timeline

1. Run `26378919228` on head `ed31b2d4a76de0fc404089746d280b1e9ef4716b` failed because `pytest` was not installed: `pytest: command not found`.
2. Run `26379178022` on head `b7be44463dd2107428d27165c564e62637576cdd` advanced to pytest collection but failed because `respx` was missing.
3. Run `26379324415` on head `9940a9a78bad0694ce9066528a8f40067128eb2f` installed dependencies and ran the suite, then failed inside backend+cockpit pytest with 65 failures.

## Current Failure Clusters

Confirmed clusters from the latest failed log:

- Architecture invariant violations:
  - `test_no_sqlite_usage_in_backend_runtime` detects `sqlite3` imports in backend runtime files.
  - `test_no_uuid4_usage_inside_process_document` detects `uuid4` inside `process_document`.
  - Cursor rule compliance also fails on sqlite/runtime and random UUID checks.
- Vector ID / ingestion invariant regressions:
  - deterministic vector ID tests did not capture expected point IDs or points.
- Missing repository fixture asset:
  - `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist` expects a PDF under `financial-engine_v2/data/asx/docs/10X/...` that is absent in the runner checkout.
- News/Qdrant script contract drift:
  - `scripts.load_news_to_qdrant` lacks expected `resolve_ollama_url`.
  - related stats payload lacks `ollama_url`.
- Redis-backed execution leak into CI:
  - `test_process_document_api_passes_method_and_strict_flag` attempts Redis/Celery connection and fails with `Error 111 connecting to 127.0.0.1:6379`.
- Cockpit service and router test contract drift:
  - multiple mocked chat-controller constructors reject the new `llm_client` keyword.
  - router tests expect older API/local policy behavior.
  - subagent tests fail with `RuntimeError: There is no current event loop in thread 'MainThread'`.
- Marketplace, memo routing, source metadata, and orchestrator expectations:
  - marketplace benchmark/value tests expect scored state but receive stale or empty state.
  - memo signal routing expects stored routed signals but gets none.
  - source metadata expects `financial_truth` only but receives an additional `financial_truth_numeric`.

## Classification

This is a suite-readiness/product-contract failure, not a current CI dependency failure.

The first two failed runs exposed missing CI dependency setup (`pytest`, then `respx`), but the current head has moved past those. The current failure means the broad backend+cockpit suite is exercising multiple known or newly exposed runtime architecture, fixture, dependency-isolation, and test-contract gaps.

## Minimal Child Fix Tasks

Recommended split, because one PR-local fix would be too broad:

1. `ci_backend_cockpit_suite_triage_matrix_v1_20260525`
   - Reproduce and classify the 65 failures into existing known gaps vs true PR regressions.
   - Bound exact fix ownership per cluster.
2. `ci_redis_dependency_isolation_v1_20260525`
   - Ensure CI tests that should be unit tests do not require live Redis, or provision Redis explicitly for integration tests.
3. `ci_gold_fixture_asset_policy_v1_20260525`
   - Decide whether the 10X PDF fixture should be checked in, fetched in CI, or the test should be fixture-availability aware.
4. `ci_cockpit_mock_contract_sync_v1_20260525`
   - Update tests or adapter seams for the `llm_client` constructor contract.
5. `ci_architecture_invariant_gate_reconciliation_v1_20260525`
   - Decide whether current sqlite/uuid invariant tests are valid merge blockers for PR #39 or should be split into a dedicated architecture cleanup gate.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_ci_failure_root_cause_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; only unrelated Strategy Lab job was active.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_ci_failure_root_cause_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/pr39_ci_failure_root_cause_audit_v1_20260525.md`: passed.
- `gh pr view 39 --json ...`: passed.
- `gh pr checks 39`: returned expected nonzero because `lint-and-test` is failing.
- `gh run list --limit 20 --json ...`: passed.
- `gh run view 26379324415 --log-failed`: passed.
- `gh api repos/0rl4nd0l/tenn/actions/runs/26379324415/jobs`: passed.
- JSON validation, `git diff --check`, task-card check-diff, and registry release: passed.
