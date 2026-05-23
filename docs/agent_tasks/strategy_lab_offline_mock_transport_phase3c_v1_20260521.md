---
job_id: strategy_lab_offline_mock_transport_phase3c_v1_20260521
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md
  - docs/strategy_lab/adapter_contract_v1.md
  - docs/strategy_lab/adapter_mock_test_plan_v1.md
  - docs/strategy_lab/adapter_quarantine_policy_v1.md
  - docs/strategy_lab/adapter_request_response_envelopes_v1.md
  - docs/strategy_lab/adapter_tool_policy_v1.md
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
  - docs/strategy_lab/mock_transport_fixtures/valid_capabilities_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_market_snapshot_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_submit_backtest_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_get_backtest_result_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/valid_regime_detect_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_policy_denied_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_trading_scope_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_missing_raw_payload_ref_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_timeout_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_order_field_transport_response_v1.json
  - docs/strategy_lab/mock_transport_fixtures/invalid_store_write_transport_response_v1.json
  - tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/phase3b_input_review.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/transport_contract.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/test_files_written.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/mock_transport_test_results.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/policy_coverage_matrix.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/quarantine_coverage.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/go_no_go_phase3d.md
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/diff-check.json
---

# Task

Run Phase 3C Strategy Lab offline mock transport adapter design and test layer for QuantDinger/Tenn using the completed Phase 3B reconciled mocked adapter tests.

# Scope

Produce offline docs, JSON fixtures, stdlib `unittest` coverage, and report outputs only. The work must remain a safe extension in the Query Orchestration lane with Provenance, Evaluation, and Reporting support.

# Required Boundaries

- `strategy_lab_artifact_v1` remains authoritative.
- `strategy_lab_sidecar_artifact_v1` remains pending-review pre-envelope only.
- Helper output cannot replace the authoritative artifact envelope.
- No real adapter/client, real API/MCP transport, QuantDinger service, MCP service, Docker startup, token issuance, dependency installation, backend/runtime/Cockpit integration, artifact store, Tenn store write, production data, or paper/live/trading execution.
- Design-level mock classes/functions may exist only inside `tests/strategy_lab/**` or docs examples.
- Stop before touching runtime/backend/product code, Cockpit, DB/Qdrant/news/memory/financial-truth stores, parser/extraction/gold-label files, source registry, Docker/systemd/env/secrets, dependency files, broker/exchange config, or unrelated dirty work.

# Required Preflight

- Print current working directory, repo root, branch, HEAD, git status, worktree list, and recent commits.
- Verify whether `/home/l4nd0/tenn` is usable or a broken symlink.
- Verify task-card and registry command help.
- Validate this task card.
- Run registry `list-active`, `check-overlap`, and claim if safe.
- Inspect dirty/untracked/deleted/staged files.
- Stop if active jobs or dirty files overlap allowed docs/test/report surfaces.

# Required Inputs

Inspect Phase 3B reconciled mocked adapter tests from:

- `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521/docs/strategy_lab/**`
- `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521/tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py`
- `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521/reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/**`

Use Phase 3A, Phase 2, and Phase 2B local bundles only as supporting evidence. Mark unavailable inputs as `DATA_MISSING`.

# Required Outputs

- Phase 3B schema, fixture, payload, and vector evidence copied into `docs/strategy_lab/**` for local parse coverage.
- Phase 3C mock transport docs under `docs/strategy_lab/mock_transport/`.
- Phase 3C mock request/response fixtures under `docs/strategy_lab/mock_transport_fixtures/`.
- `tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py`.
- Full report bundle under `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/`.

# Required Test Coverage

- Phase 3B vectors parse.
- Phase 3C mock transport fixtures parse.
- Authoritative schema fixtures still parse.
- The Phase 3C test file imports stdlib modules only.
- Every mock request passes through policy before mock dispatch.
- Denied or forbidden scope requests do not produce artifacts.
- Trading, order, broker, exchange, token, service startup, runtime route, store-write, and production-data fields are denied.
- Only list capabilities, market snapshot read, offline mock backtest submit/result/job poll, offline mock regime detect, and local mock artifact conversion are allowed.
- Parameter sweep or structured tuning remains default-hold or `DATA_MISSING` unless evidence supports a bounded mock-only path.
- Helper output remains pre-envelope and cannot be emitted as a final Strategy Lab artifact.
- Quarantine and `DATA_MISSING` cases are explicit.
- Tests prove no fixture or vector authorizes production data, services, network transport, dependency installation, token issuance, store writes, paper/live execution, order/bot/kill-switch actions, source-registry writes, parser/gold-label writes, or holdings/watchlist/thesis mutation.

# Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`
- Claim and later release the registry job if supported and safe.
- `python3 -m unittest tests.strategy_lab.test_strategy_lab_offline_mock_transport_phase3c -v`
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`

# Phase 3D Recommendation

Recommend exactly one:

- `GO_PHASE3D_OFFLINE_ADAPTER_CONTRACT_REVIEW_ONLY`
- `DEFER_MOCK_TRANSPORT_TEST_GAPS`
- `DEFER_SCHEMA_OR_POLICY_REVIEW_REQUIRED`
- `REJECT_TOO_RISKY`
