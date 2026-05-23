---
job_id: strategy_lab_mocked_adapter_design_phase3_v1_20260520
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520
allowed_files:
  - docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md
  - docs/strategy_lab/**
  - docs/strategy_lab/adapter_contract_v1.md
  - docs/strategy_lab/adapter_tool_policy_v1.md
  - docs/strategy_lab/adapter_request_response_envelopes_v1.md
  - docs/strategy_lab/adapter_quarantine_policy_v1.md
  - docs/strategy_lab/adapter_mock_test_plan_v1.md
  - docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json
  - docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json
  - docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json
  - docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json
  - docs/strategy_lab/mock_payloads/mock_data_missing_result_v1.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/**
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/phase2_schema_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/tool_policy_matrix.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/mock_envelope_review.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/quarantine_and_error_policy.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/go_no_go_phase3b.md
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/diff-check.json
---

# Task

Run Phase 3A Strategy Lab mocked adapter design-only for QuantDinger/Tenn using the completed Phase 2 artifact schema evidence.

Mode: DESIGN-ONLY SAFE EXTENSION / REPORT + DOCS + MOCK FIXTURES ONLY.

Primary lane: Query Orchestration.

Supporting lanes:

- Provenance.
- Evaluation.
- Reporting.

# Architecture Boundary

- Tenn is the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator only.
- QuantDinger outputs become Strategy Lab artifacts, never canonical financial truth.
- Strategy Lab artifacts default to `PENDING_REVIEW`.
- Tenn code must own tool execution policy, schema validation, permissions, logging, raw-output quarantine, and artifact review boundaries.
- A local llama/router may reason about an approved tool intent, but Tenn code executes and gates tool calls.
- Codex is a dev/audit agent only, not the runtime path.

# Allowed Writes

- This task card.
- `docs/strategy_lab/**`.
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/**`.

If `docs/strategy_lab/**` overlaps dirty or claimed work, stop and report the collision rather than improvising.

# Forbidden Writes

- Tenn runtime/backend/product code.
- Cockpit UI/backend code.
- DB, Qdrant, news, memory, or financial-truth stores.
- Parser, extraction, or gold-label files.
- Source-registry writes.
- Docker, systemd, env, or secrets files.
- QuantDinger install/runtime directories.
- MCP adapter/client implementation.
- Real API client code.
- Broker, exchange, paper, or live execution configs.
- Dependency installation or package lock changes.
- Unrelated dirty or untracked files.

# Required Preflight

Run and report:

- `pwd`.
- `git rev-parse --show-toplevel`.
- `git branch --show-current`.
- `git rev-parse HEAD`.
- `git status --short --untracked-files=all`.
- `git worktree list`.
- Recent commits.
- Current task-card and registry command help before relying on exact commands.
- Task-card validation if supported.
- Registry `list-active` if supported.
- Registry `check-overlap` after task-card creation if supported.
- Registry claim if safe and supported.

Inspect dirty, untracked, and deleted files. Stop if active jobs or dirty files overlap the allowed docs/schema/report surfaces. Do not clean, stash, reset, remove, or modify unrelated dirty files.

# Inputs

Inspect Phase 2 schema docs and fixtures at:

- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_schema_v1.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_schema_v1.schema.json`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_fixtures/`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/`

Inspect Phase 1 sandbox and Phase 0 fit-audit report bundles if present. If any input path is unavailable, mark it `DATA_MISSING` and continue only if the remaining Phase 2 schema evidence is sufficient for a design-only adapter contract.

# Scope

Define the mocked adapter contract only. Describe future client/wrapper boundaries, strict tool allowlist, blocked tool surfaces, request/response envelopes, artifact normalization mapping, error and quarantine policy, mock-only future test plan, and Phase 3B go/no-go.

Do not implement a real adapter/client, import or install MCP/QuantDinger dependencies, start Docker, start QuantDinger, start MCP, issue tokens, add secrets/env config, set up broker/exchange/paper/live execution, modify Tenn runtime/backend/Cockpit code, implement an artifact store, write Tenn stores, access production data, or add autonomous loops/scheduled jobs.

# Required Outputs

- `docs/strategy_lab/adapter_contract_v1.md`
- `docs/strategy_lab/adapter_tool_policy_v1.md`
- `docs/strategy_lab/adapter_request_response_envelopes_v1.md`
- `docs/strategy_lab/adapter_quarantine_policy_v1.md`
- `docs/strategy_lab/adapter_mock_test_plan_v1.md`
- `docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json`
- `docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json`
- `docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/README.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/phase2_schema_review.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/tool_policy_matrix.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/mock_envelope_review.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/quarantine_and_error_policy.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/go_no_go_phase3b.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/status.json`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/diff-check.json` if supported.

# Validation

Run and report:

- Task-card validation if supported.
- Registry `list-active`, `check-overlap`, claim, release, and final `list-active` if supported.
- JSON parse validation for all mock payload JSON files.
- JSON parse validation for existing Phase 2 schema and fixtures if referenced locally.
- Markdown/doc sanity check if repo has one.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md` if supported.
- Final `git status --short --untracked-files=all`.

Prove all written files are inside allowed paths and no runtime/product code, production data, Tenn stores, services, tokens, dependencies, or paper/live execution were touched.

# Go/No-Go

Recommend exactly one:

- `GO_PHASE3B_MOCKED_ADAPTER_TESTS_ONLY`
- `DEFER_SCHEMA_OR_PAYLOAD_GAPS`
- `REJECT_TOO_RISKY`
