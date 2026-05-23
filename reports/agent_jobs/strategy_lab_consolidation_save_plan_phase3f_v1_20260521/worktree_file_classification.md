# Worktree File Classification

## Classification Legend

- `active_candidate_input`: candidate Strategy Lab docs, schema, fixture, vector,
  or test material that may become authoritative if later saved under a separate
  approved task.
- `report_only_evidence`: report bundle output that should be preserved as
  audit/history evidence if desired.
- `pending_review_helper_candidate`: helper material that may inform future
  work but must not replace the authoritative envelope.
- `archive_only`: older or duplicate evidence that should not be promoted as the
  main source.
- `duplicate_superseded`: candidate content superseded by later authoritative
  schema or transport evidence.
- `generated_exclude`: generated artifacts to exclude from preservation.
- `DATA_MISSING`: unavailable evidence or unproven committed-baseline state.

## Phase 2 Authoritative Artifact Schema

Path:
`/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520`

Current state: untracked task card, docs, schema, and fixtures; ignored report
bundle.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md` | untracked | report/task-history evidence |
| `docs/strategy_lab/artifact_schema_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_schema_v1.schema.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json` | untracked | active_candidate_input |
| `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/**` | ignored | report_only_evidence |

Decision: this is the authoritative schema candidate and should be the baseline
source for `strategy_lab_artifact_v1`, subject to a future approved save action.

## Phase 2B Helper Candidate

Path:
`/home/l4nd0/tenn-strategy-lab-quantdinger-phase2-artifact-schema-v1-20260521`

Current state: untracked helper doc, backend helper module, test, fixtures;
ignored report, raw payload, and normalized artifact outputs.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md` | untracked | report/task-history evidence |
| `docs/strategy_lab_quantdinger_artifact_schema.md` | untracked | pending_review_helper_candidate |
| `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py` | untracked | pending_review_helper_candidate |
| `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py` | untracked | pending_review_helper_candidate |
| `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_backtest_summary.json` | untracked | pending_review_helper_candidate |
| `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_regime_summary.json` | untracked | pending_review_helper_candidate |
| `reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/**` | ignored | report_only_evidence and pending_review_helper_candidate |

Decision: keep as pending-review helper evidence. Do not promote helper code or
`strategy_lab_sidecar_artifact_v1` as authoritative over
`strategy_lab_artifact_v1`.

## Phase 3A Mocked Adapter Design

Path:
`/home/l4nd0/tenn-strategy-lab-mocked-adapter-design-phase3-v1-20260520`

Current state: staged additions. No untracked or modified work outside the
staged additions was observed.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md` | staged add | report/task-history evidence |
| `docs/strategy_lab/adapter_contract_v1.md` | staged add | active_candidate_input |
| `docs/strategy_lab/adapter_mock_test_plan_v1.md` | staged add | active_candidate_input |
| `docs/strategy_lab/adapter_quarantine_policy_v1.md` | staged add | active_candidate_input |
| `docs/strategy_lab/adapter_request_response_envelopes_v1.md` | staged add | active_candidate_input |
| `docs/strategy_lab/adapter_tool_policy_v1.md` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_data_missing_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json` | staged add | active_candidate_input |
| `docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json` | staged add | active_candidate_input |
| `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/**` | staged add | report_only_evidence |

Decision: candidate design baseline, but the staged state requires a separate
explicit unstage/commit/archive decision before use as current baseline.

## Phase 3B Reconciled Mocked Adapter Tests

Path:
`/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`

Current state: untracked task card, docs, vectors, and test; ignored report
bundle and pycache.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md` | untracked | report/task-history evidence |
| `docs/strategy_lab/artifact_schema_v1.md` | untracked | active_candidate_input, duplicate of Phase 2 authoritative schema candidate |
| `docs/strategy_lab/artifact_schema_v1.schema.json` | untracked | active_candidate_input, duplicate of Phase 2 authoritative schema candidate |
| `docs/strategy_lab/artifact_fixtures/*.json` | untracked | active_candidate_input, duplicate of Phase 2 authoritative fixtures |
| `docs/strategy_lab/adapter_contract_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/adapter_mock_test_plan_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/adapter_quarantine_policy_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/adapter_request_response_envelopes_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/adapter_tool_policy_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_payloads/*.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/artifact_invariant_cases_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json` | untracked | active_candidate_input |
| `tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py` | untracked | active_candidate_input |
| `reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/**` | ignored | report_only_evidence |
| `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/**` | ignored | archive_only, duplicate_superseded |
| `tests/strategy_lab/__pycache__/**` | ignored | generated_exclude |

Decision: preserve the unique Phase 3B vectors/test as candidate inputs. Treat
copied Phase 2/3A docs as consolidation copies, not independent authorities.

## Phase 3C Offline Mock Transport

Path:
`/home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`

Current state: untracked task card, docs, vectors, mock transport docs/fixtures,
and test; ignored report bundle and pycache.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md` | untracked | report/task-history evidence |
| `docs/strategy_lab/artifact_schema_v1.md` | untracked | active_candidate_input, duplicate of Phase 2 authoritative schema candidate |
| `docs/strategy_lab/artifact_schema_v1.schema.json` | untracked | active_candidate_input, duplicate of Phase 2 authoritative schema candidate |
| `docs/strategy_lab/artifact_fixtures/*.json` | untracked | active_candidate_input, duplicate of Phase 2 authoritative fixtures |
| `docs/strategy_lab/adapter_*.md` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_payloads/*.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_test_vectors/*.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport/offline_mock_transport_contract_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport/offline_mock_transport_lifecycle_v1.md` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/valid_capabilities_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/valid_get_backtest_result_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/valid_market_snapshot_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/valid_regime_detect_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/valid_submit_backtest_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_missing_raw_payload_ref_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_order_field_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_policy_denied_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_store_write_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_timeout_transport_response_v1.json` | untracked | active_candidate_input |
| `docs/strategy_lab/mock_transport_fixtures/invalid_trading_scope_transport_response_v1.json` | untracked | active_candidate_input |
| `tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py` | untracked | active_candidate_input |
| `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/**` | ignored | report_only_evidence |
| `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/**` | ignored | archive_only, duplicate_superseded |
| `tests/strategy_lab/__pycache__/**` | ignored | generated_exclude |

Decision: preserve the unique Phase 3C mock transport docs, fixtures, and test
as the latest offline transport candidate, after later approved consolidation.

## Phase 3D Contract Review

Path:
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Current state: report bundle present under ignored `reports/agent_jobs`; task
card remains untracked in the current checkout.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md` | untracked | report/task-history evidence |
| `reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/**` | ignored | report_only_evidence |

Decision: preserve as task-history and contract-review report evidence. Do not
reinterpret it as implementation approval.

## Phase 3E Implementation Plan

Path:
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Current state: report bundle present under ignored `reports/agent_jobs`; task
card remains untracked in the current checkout.

| File or group | Current git state | Classification |
|---|---:|---|
| `docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md` | untracked | report/task-history evidence |
| `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/**` | ignored | report_only_evidence |

Decision: preserve as the immediate Phase 3F input. It recommends
`GO_PHASE3F_CONSOLIDATION_SAVE_PLAN_ONLY`.

## Cross-Worktree Classification Result

- Active authoritative candidate inputs: Phase 2 schema/fixtures, Phase 3A
  adapter docs/mock payloads, Phase 3B test vectors/test, Phase 3C mock
  transport docs/fixtures/test.
- Report-only evidence: Phase 2, 2B, 3A, 3B, 3C, 3D, 3E report bundles.
- Pending-review helper candidate: Phase 2B helper schema/doc/module/test,
  fixture summaries, raw payload summaries, and normalized helper artifacts.
- Archive-only or duplicate/superseded: older `strategy_lab_quantdinger_framework_v1_20260520`
  report bundles in Phase 3B and Phase 3C, plus helper material that conflicts
  with the authoritative Phase 2 schema.
- Generated/exclude: Phase 3B and Phase 3C `__pycache__` files.
- DATA_MISSING: committed baseline proof and approved save destination for each
  candidate group.
