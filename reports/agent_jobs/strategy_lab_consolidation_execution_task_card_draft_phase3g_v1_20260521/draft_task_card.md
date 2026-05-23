# Draft Future Task Card

This is a draft for the future consolidation execution task. It is not active,
was not claimed, and does not authorize mutation by itself.

```markdown
---
job_id: strategy_lab_consolidation_execution_phase3g_v1_20260521
lane: Provenance
owner: Codex
mutation_mode: safe_extension
approval_required: true
allow_audit_code_changes: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_consolidation_execution_phase3g_v1_20260521.md
  - docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md
  - docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md
  - docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md
  - docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_mock_transport_phase3c_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md
  - docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md
  - docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md
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
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/**
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/**
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/**
  - reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/**
  - reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/**
  - reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521/**
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/**
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/**
  - reports/agent_jobs/strategy_lab_consolidation_execution_phase3g_v1_20260521/**
---

# Strategy Lab Phase 3G Consolidation Execution

## Objective

Execute the approved Strategy Lab consolidation/save plan from Phase 3F by
preserving selected Phase 2/2B/3A/3B/3C/3D/3E/3F task cards, docs, tests, and
report evidence into the current baseline without implementing runtime,
backend, Cockpit, store, dependency, service, token, production-data, or trading
behavior.

## Approval Gate

This task is mutation-capable and must not be run unless the user explicitly
approves actual consolidation mutation after reviewing the Phase 3F and Phase
3G draft-only reports.

## Source Worktrees

- Phase 2 authoritative schema:
  `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520`
- Phase 2B helper candidate:
  `/home/l4nd0/tenn-strategy-lab-quantdinger-phase2-artifact-schema-v1-20260521`
- Phase 3A mocked adapter design:
  `/home/l4nd0/tenn-strategy-lab-mocked-adapter-design-phase3-v1-20260520`
- Phase 3B reconciled mocked adapter tests:
  `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- Phase 3C offline mock transport:
  `/home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`
- Phase 3D/3E/3F current-baseline report/task-card evidence:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

## Required Actions

- Save Phase 2 authoritative `strategy_lab_artifact_v1` schema docs, JSON
  schema, and fixtures as baseline candidates.
- Save Phase 3A adapter docs and mock payloads as baseline candidates, after
  explicitly resolving the current staged state in the Phase 3A worktree.
- Save Phase 3B unique mock test vectors and unittest as baseline candidates.
- Save Phase 3C unique mock transport docs, fixtures, and unittest as baseline
  candidates.
- Preserve Phase 2/2B/3A/3B/3C/3D/3E/3F task cards as task-history evidence if
  keeping the phase chain auditable in git.
- Force-add selected ignored report bundles only if report evidence should live
  in git.
- Keep Phase 2B helper material pending-review and out of runtime/backend
  wiring.
- Record duplicate older `strategy_lab_quantdinger_framework_v1_20260520`
  report bundles as archive-only evidence; do not promote them as current
  baseline.
- Exclude Phase 3B and Phase 3C `__pycache__` files.

## Forbidden Actions

- Do not implement real adapter/client code.
- Do not implement real transport.
- Do not start QuantDinger, MCP, Docker, Tenn runtime services, or Cockpit.
- Do not issue tokens or add secrets/env config.
- Do not install dependencies or modify dependency files or lockfiles.
- Do not modify Tenn runtime/backend/product code outside the exact allowed
  Strategy Lab docs/tests/report/task-card surfaces.
- Do not modify Cockpit.
- Do not implement an artifact store.
- Do not write DB, Qdrant, news, memory, or financial-truth stores.
- Do not modify parser/extraction/gold-label files.
- Do not write source-registry files.
- Do not access production data.
- Do not configure broker/exchange/paper/live execution.
- Do not add autonomous loops or scheduled jobs.

## Validation

- Validate this task card.
- Run registry `list-active`, `check-overlap`, claim, and release if supported.
- Confirm source worktree branch/HEAD/status before copying any approved
  candidate file.
- Run markdown sanity checks if available.
- Run JSON parse validation for all saved JSON fixtures and status files.
- Run the offline stdlib Strategy Lab tests if saved:
  `python3 -m unittest tests.strategy_lab.test_strategy_lab_mocked_adapter_phase3b_reconciled -v`
  and
  `python3 -m unittest tests.strategy_lab.test_strategy_lab_offline_mock_transport_phase3c -v`.
- Run `git diff --check`.
- Run `git diff --cached --check` if staged files exist.
- Run `agent_job_contract.py check-diff`.
- Final git status.
- Prove no forbidden runtime, Cockpit, store, dependency, service, token,
  production-data, or trading surface changed.
```

## Draft Notes

- The future execution card is intentionally approval-gated with
  `approval_required: true`.
- It lists report bundles with globs because report directories contain
  ignored artifacts; an execution task may need to replace these with exact
  report-child paths if the current validator requires exact file entries.
- It excludes generated pycache by not listing any `__pycache__` path.
- It does not list Phase 2B backend helper code as a baseline runtime candidate;
  Phase 2B remains pending-review helper evidence only.
