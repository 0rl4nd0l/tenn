---
job_id: strategy_lab_phase3g_mergeback_v1_20260524
lane: Provenance
owner: Codex
mutation_mode: safe_extension
approval_required: true
allow_audit_code_changes: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524

allowed_files:
  - docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md
  - reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/validation.md
  - reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_phase3g_mergeback_v1_20260524/diff-check.json
  - docs/agent_tasks/strategy_lab_consolidation_execution_phase3g_v1_20260521.md
  - docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md
  - docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md
  - docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md
  - docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md
  - docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md
  - docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md
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
  - docs/strategy_lab/adapter_mock_test_plan_v1.md
  - docs/strategy_lab/adapter_quarantine_policy_v1.md
  - docs/strategy_lab/adapter_request_response_envelopes_v1.md
  - docs/strategy_lab/adapter_tool_policy_v1.md
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
  - docs/strategy_lab/mock_test_vectors/artifact_invariant_cases_v1.json
  - docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json
  - docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json
  - docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json
  - docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json
  - docs/strategy_lab/mock_transport/offline_mock_transport_contract_v1.md
  - docs/strategy_lab/mock_transport/offline_mock_transport_lifecycle_v1.md
  - docs/strategy_lab/mock_transport_fixtures/invalid_missing_raw_payload_ref_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_order_field_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_policy_denied_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_store_write_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_timeout_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_trading_scope_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_capabilities_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_get_backtest_result_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_market_snapshot_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_regime_detect_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_submit_backtest_transport_response_v1.json
  - tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py
  - tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/diff-check.json
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/go_no_go_phase3.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/phase1_payload_mapping.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/schema_invariants.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/validation_notes.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/backtest_run.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/regime_breakdown.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/raw_payloads/phase1_backtest_normalized_summary.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/raw_payloads/phase1_regime_detect_normalized_summary.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/schema_contract.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/security_boundaries.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/validation.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/diff-check.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/go_no_go_phase3b.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/mock_envelope_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/phase2_schema_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/quarantine_and_error_policy.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/tool_policy_matrix.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/go_no_go_phase3c.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/helper_mapping_coverage.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/mock_test_results.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/policy_coverage_matrix.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/quarantine_coverage.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/reconciliation_input_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/test_files_written.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/go_no_go_phase3d.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/mock_transport_test_results.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/phase3b_input_review.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/policy_coverage_matrix.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/quarantine_coverage.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/test_files_written.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/transport_contract.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/artifact_boundary_review.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/contract_completeness.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/gaps_and_risks.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/go_no_go_phase3e.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/safety_boundary_review.md
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/future_phase_map.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/go_no_go_next.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/offline_implementation_plan.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/risk_and_hard_stops.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/worktree_consolidation_readiness.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/future_action_matrix.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/phase3g_recommendation.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preservation_model.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/worktree_file_classification.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/draft_task_card.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/source_worktree_recheck.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/action_matrix_applied.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/files_preserved.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/files_excluded.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/report_evidence_preservation.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/validation_results.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/boundary_check.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/go_no_go_next.md
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/diff-check.json
---

# Strategy Lab Phase 3G Mergeback

## Objective

Cherry-pick the approved isolated Phase 3G consolidation commit
`6d8ecff855a8c7f27d5b270bd0ed01473d696ffb` onto current baseline
`8729c7329630099465cd2264a63b7c1b83b61a20` from a clean merge-back worktree.

## Boundaries

- Do not merge the isolated branch tip, because it was based before later
  Cockpit commits.
- Do not touch Cockpit product code, runtime/backend/product code, Tenn stores,
  dependencies, services, tokens, production data, or paper/live/trading paths.
- Do not clean, stage, unstage, stash, reset, remove, or mutate dirty files in
  the shared checkout.
- Preserve only the Phase 3G evidence commit plus this merge-back task/report
  evidence.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md --repo-root .`
- `git cherry-pick 6d8ecff855a8c7f27d5b270bd0ed01473d696ffb`
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- Allowlisted JSON parse validation.
- Focused Strategy Lab unittest validation if Python environment supports it.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md --repo-root .`
- Release registry and verify final status.

## Definition Of Done

- The current baseline branch has a merge-back commit containing Phase 3G
  evidence without undoing Cockpit commits.
- The changed-file set is within this task card.
- Registry is released.
- Shared checkout dirty work remains untouched.
