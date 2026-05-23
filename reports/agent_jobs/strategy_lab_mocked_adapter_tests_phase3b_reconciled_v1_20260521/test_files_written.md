# Test Files Written

## Task Card

- `docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md`

## Copied/Recreated Schema And Design Inputs

- `docs/strategy_lab/artifact_schema_v1.md`
- `docs/strategy_lab/artifact_schema_v1.schema.json`
- `docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json`
- `docs/strategy_lab/adapter_contract_v1.md`
- `docs/strategy_lab/adapter_tool_policy_v1.md`
- `docs/strategy_lab/adapter_request_response_envelopes_v1.md`
- `docs/strategy_lab/adapter_quarantine_policy_v1.md`
- `docs/strategy_lab/adapter_mock_test_plan_v1.md`
- `docs/strategy_lab/mock_payloads/*.json`

One copied Phase 3A mock payload was reconciled locally:

- `docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json` now includes the required hard flags for its emitted `backtest_run` artifact mapping.

## New Phase 3B Mock Test Vectors

- `docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json`
- `docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json`
- `docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json`
- `docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json`
- `docs/strategy_lab/mock_test_vectors/artifact_invariant_cases_v1.json`

## New Offline Tests

- `tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py`

The test file imports only `json`, `pathlib`, `re`, and `unittest`.
