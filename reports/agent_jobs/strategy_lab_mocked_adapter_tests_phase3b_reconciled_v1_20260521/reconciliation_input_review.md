# Reconciliation Input Review

## Reconciliation Report

All required reconciliation report files were available and inspected:

- `/home/l4nd0/tenn-strategy-lab-schema-lineage-reconciliation-v1-20260521/reports/agent_jobs/strategy_lab_schema_lineage_reconciliation_v1_20260521/README.md`
- `/home/l4nd0/tenn-strategy-lab-schema-lineage-reconciliation-v1-20260521/reports/agent_jobs/strategy_lab_schema_lineage_reconciliation_v1_20260521/schema_diff_summary.md`
- `/home/l4nd0/tenn-strategy-lab-schema-lineage-reconciliation-v1-20260521/reports/agent_jobs/strategy_lab_schema_lineage_reconciliation_v1_20260521/phase3_implications.md`
- `/home/l4nd0/tenn-strategy-lab-schema-lineage-reconciliation-v1-20260521/reports/agent_jobs/strategy_lab_schema_lineage_reconciliation_v1_20260521/recommendation.md`
- `/home/l4nd0/tenn-strategy-lab-schema-lineage-reconciliation-v1-20260521/reports/agent_jobs/strategy_lab_schema_lineage_reconciliation_v1_20260521/status.json`

Confirmed reconciliation facts:

- Decision: `ACCEPT_PHASE2B_SCHEMA_HELPER_PENDING_REVIEW`.
- Next-phase recommendation: `GO_PHASE3B_RERUN_WITH_RECONCILED_SCHEMA`.
- Earlier Phase 2 `strategy_lab_artifact_v1` remains authoritative.
- 2026-05-21 helper `strategy_lab_sidecar_artifact_v1` remains a pending-review pre-envelope candidate.
- Prior Phase 3B path `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-v1-20260520` remains `DATA_MISSING`.

## Phase 2 Authoritative Schema

Available and copied into this worktree:

- `docs/strategy_lab/artifact_schema_v1.md`
- `docs/strategy_lab/artifact_schema_v1.schema.json`
- `docs/strategy_lab/artifact_fixtures/*.json`

Copied fixtures:

- `invalid_canonical_truth_v1.json`
- `invalid_credentials_field_v1.json`
- `invalid_execution_allowed_v1.json`
- `invalid_financial_truth_label_v1.json`
- `invalid_memory_or_financial_truth_write_v1.json`
- `invalid_missing_provenance_v1.json`
- `valid_backtest_run_v1.json`
- `valid_regime_breakdown_v1.json`
- `valid_strategy_idea_v1.json`

## Phase 3A Mocked Adapter Design

Available and copied into this worktree:

- `adapter_contract_v1.md`
- `adapter_tool_policy_v1.md`
- `adapter_request_response_envelopes_v1.md`
- `adapter_quarantine_policy_v1.md`
- `adapter_mock_test_plan_v1.md`
- all ten Phase 3A mock payload JSON files under `docs/strategy_lab/mock_payloads/`

The Phase 3A report `go_no_go_phase3b.md` recommended `GO_PHASE3B_MOCKED_ADAPTER_TESTS_ONLY`.

The literal input path containing `tenn-strategy-lab-mocked-adapter-design-phase3_v1_20260520` was `DATA_MISSING`; the available sibling worktree with the expected report was `/home/l4nd0/tenn-strategy-lab-mocked-adapter-design-phase3-v1-20260520`.

## Phase 2B Helper Candidate

Available and inspected as pending-review evidence only:

- `docs/strategy_lab_quantdinger_artifact_schema.md`
- `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_backtest_summary.json`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_regime_summary.json`
- `reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/backtest_run.json`
- `reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/regime_breakdown.json`

The helper output uses `schema_version=strategy_lab_sidecar_artifact_v1` and an `observations` envelope. It was not imported by the Phase 3B tests and was not copied as authoritative schema.

## DATA_MISSING

- Existing verified Phase 3B baseline: `DATA_MISSING`.
- Literal Phase 3A go/no-go path with `phase3_v1` directory spelling: `DATA_MISSING`; the `phase3-v1` worktree path was available and inspected.
- Helper evidence for `parameter_sweep`, broad `risk_report`, `factor_test`, and `portfolio_experiment`: `DATA_MISSING`.
- Phase 1 benchmark/provider/hash fields remain `DATA_MISSING` where the copied authoritative fixtures already mark them.
