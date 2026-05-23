---
job_id: strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md
  - docs/strategy_lab/artifact_schema_v1.md
  - docs/strategy_lab/artifact_schema_v1.schema.json
  - docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json
  - docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json
  - docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json
  - docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json
  - docs/strategy_lab/adapter_contract_v1.md
  - docs/strategy_lab/adapter_tool_policy_v1.md
  - docs/strategy_lab/adapter_request_response_envelopes_v1.md
  - docs/strategy_lab/adapter_quarantine_policy_v1.md
  - docs/strategy_lab/adapter_mock_test_plan_v1.md
  - docs/strategy_lab/mock_payloads/mock_data_missing_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json
  - docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json
  - docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json
  - docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json
  - docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json
  - docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json
  - docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json
  - docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json
  - docs/strategy_lab/mock_test_vectors/artifact_invariant_cases_v1.json
  - tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/reconciliation_input_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/test_files_written.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/mock_test_results.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/policy_coverage_matrix.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/helper_mapping_coverage.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/quarantine_coverage.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/go_no_go_phase3c.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/diff-check.json
---

# Task

Run the Phase 3B Strategy Lab mocked adapter test rerun with the reconciled QuantDinger/Tenn schema boundary.

# Scope

Produce offline docs, mock JSON vectors, stdlib `unittest` tests, and reports only. Keep `strategy_lab_artifact_v1` as the authoritative artifact envelope. Treat the 2026-05-21 `strategy_lab_sidecar_artifact_v1` helper output as pending-review pre-envelope evidence that must either map into the full authoritative envelope or remain quarantined.

# Boundaries

- Do not implement a real adapter or client.
- Do not import or install QuantDinger, MCP, Docker, broker/exchange, requests, httpx, aiohttp, socket networking clients, or `jsonschema`.
- Do not start services or issue tokens.
- Do not touch Tenn runtime/backend/product code, Cockpit, stores, DB, Qdrant, news, memory, financial-truth persistence, parser/extraction/gold-label files, source-registry writes, Docker/systemd/env/secrets, dependency files, or lockfiles.
- Do not use production data.
- Do not perform paper, live, trading, order, bot, or kill-switch execution.
- Stop if dirty files or active registry jobs overlap the allowed docs, tests, or report paths.

# Required Inputs

Inspect and classify available local evidence from:

- the 2026-05-21 schema-lineage reconciliation report,
- the earlier Phase 2 `strategy_lab_artifact_v1` authoritative schema and fixtures,
- the Phase 3A mocked adapter design and mock payloads,
- the 2026-05-21 Phase 2B helper candidate and normalized artifacts.

Mark unavailable inputs as `DATA_MISSING` and continue only if enough evidence remains for offline mocked tests.

# Required Outputs

- copied or recreated authoritative schema/design/mock payload files under `docs/strategy_lab/`,
- reconciled Phase 3B mock vectors under `docs/strategy_lab/mock_test_vectors/`,
- `tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py`,
- the report bundle under `reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/`.

# Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- claim and later release the job if overlap checks are safe
- `python -m unittest tests.strategy_lab.test_strategy_lab_mocked_adapter_phase3b_reconciled -v`
- `git diff --check`
- `git diff --cached --check` if staged files exist
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`

# Phase 3C Recommendation

Recommend exactly one of:

- `GO_PHASE3C_OFFLINE_MOCK_TRANSPORT_ADAPTER_ONLY`
- `DEFER_MOCK_TEST_GAPS`
- `DEFER_SCHEMA_OR_POLICY_REVIEW_REQUIRED`
- `REJECT_TOO_RISKY`
