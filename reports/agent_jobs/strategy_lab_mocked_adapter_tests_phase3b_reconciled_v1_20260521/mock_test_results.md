# Mock Test Results

## Command Results

Preferred command:

- `python -m unittest tests.strategy_lab.test_strategy_lab_mocked_adapter_phase3b_reconciled -v`
- Result: failed to start because `/bin/bash: line 1: python: command not found`.

Executed stdlib equivalent available in this shell:

```text
python3 -m unittest tests.strategy_lab.test_strategy_lab_mocked_adapter_phase3b_reconciled -v
test_authoritative_schema_baseline_remains_phase2_artifact_v1 ... ok
test_blocked_surfaces_are_default_denied ... ok
test_evidence_backed_type_limits_are_enforced ... ok
test_forbidden_evidence_labels_are_rejected_or_flagged ... ok
test_helper_candidate_is_pre_envelope_only ... ok
test_helper_to_authoritative_mapping_contains_full_required_fields ... ok
test_json_parse_coverage ... ok
test_no_store_write_contract_authorizes_no_store_mutation ... ok
test_quarantine_and_data_missing_cases_cover_required_failures ... ok
test_required_strategy_lab_artifact_flags_are_preserved ... ok
test_static_import_hygiene_for_phase3b_tests_and_vectors ... ok
test_tool_allowlist_entries_declare_required_policy_fields ... ok

Ran 12 tests in 0.011s

OK
```

## Coverage Summary

- JSON parse coverage: authoritative schema, Phase 2 fixtures, Phase 3A mock payloads, and Phase 3B vectors.
- Authoritative baseline: `strategy_lab_artifact_v1` docs/schema/fixtures remain authoritative.
- Helper status: `strategy_lab_sidecar_artifact_v1` remains pending-review pre-envelope only.
- Helper mapping: `backtest_run` and `regime_breakdown` map only through full `strategy_lab_artifact_v1` fixture envelopes.
- Flags: all valid mapped artifacts preserve false truth/store/execution flags and `PENDING_REVIEW`.
- Type limits: only `backtest_run` and `regime_breakdown` are evidence-backed.
- Tool policy: allow/mock/default-hold/conditional local-conversion entries declare inputs, outputs, raw refs, quarantine, DATA_MISSING, audit logs, rate expectations, and human review.
- Blocked surfaces: credential, token, order, trading, Tenn store, parser/gold-label, and source-registry surfaces deny by default.
- Quarantine: helper pre-envelope promotion, unavailable sidecar, timeout, malformed output, schema failure, policy denial, forbidden scope, missing evidence, credentials, orders, unexpected types, and suspected execution surfaces are covered.
- Static hygiene: test file does not import forbidden modules or the Phase 2B backend helper.

## Validation Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md`: `ok=true`.
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`: `ok=true`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`: `ok=true`, no issues.
- `scripts/check_markdown_hygiene.sh`: `[markdown-hygiene] Internal markdown link scan passed.`
- `git diff --check`: passed with no output.
- `git diff --cached --name-only`: no staged files, so `git diff --cached --check` was not required.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521.md --repo-root /home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`: `ok=true`, `disallowed_files=[]`.

## Boundary Checks

- Dependency files and lockfiles: no changes.
- Runtime/backend/Cockpit paths: no changes.
- Report directory status: ignored by git as `!! reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/`, with all required report files present locally.
- Process check found no QuantDinger or `docker compose` process for this job. Existing Serena/Exa MCP helper processes were already running from May 20, 2026 before this job and were not started by this Phase 3B work.
