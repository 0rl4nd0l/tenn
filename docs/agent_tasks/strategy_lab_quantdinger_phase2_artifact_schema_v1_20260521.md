---
job_id: strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md
  - docs/strategy_lab_quantdinger_artifact_schema.md
  - financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py
  - financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py
  - financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_backtest_summary.json
  - financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_regime_summary.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/schema_contract.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/validation.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/security_boundaries.md
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/raw_payloads/phase1_backtest_normalized_summary.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/raw_payloads/phase1_regime_detect_normalized_summary.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/backtest_run.json
  - reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/normalized_artifacts/regime_breakdown.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521
mutation_mode: safe_extension
production_data_access: false
---

# Strategy Lab QuantDinger Phase 2 Artifact Schema

Implement the bounded Phase 2 follow-up recommended by the Phase 1 QuantDinger sandbox report: define an offline Strategy Lab artifact schema and validator for pending-review QuantDinger sidecar outputs.

## Scope

- Use only saved Phase 1 public/sample payload summaries from `reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520/raw_payloads/`.
- Produce schema documentation, offline validator/normalizer code, focused fixtures/tests, and an evidence report bundle.
- Map observed QuantDinger payloads only to pending-review Strategy Lab artifact shapes for:
  - `backtest_run`
  - `regime_breakdown`
  - `parameter_sweep`
  - `risk_report`
  - `factor_test`
  - `portfolio_experiment`
- Preserve these required truth and execution flags on every accepted artifact:
  - `canonical_financial_truth=false`
  - `production_data_access=false`
  - `may_write_db=false`
  - `may_write_qdrant=false`
  - `may_write_memory=false`
  - `may_write_financial_truth=false`
  - `execution_allowed=false`
  - `review_status=PENDING_REVIEW`

## Hard Boundaries

- No Tenn runtime integration.
- No Cockpit UI or backend route edits.
- No Tenn DB, Qdrant, news, memory, or financial-truth writes.
- No parser, extraction, or gold-label edits.
- No Tenn env or secrets reads/writes.
- No broker or exchange credentials.
- No paper or live execution.
- No live QuantDinger service startup.
- No network calls to QuantDinger.
- No production Tenn data.
- No writes outside `allowed_files`.

## Required Validation

- Validate this task card.
- Run `agent_job_registry.py check-overlap` and claim only if no active lane/file collision exists.
- Run focused schema tests.
- Run `git diff --check`.
- Run `agent_job_contract.py check-diff`.
- Release the registry claim.
- Confirm final git status and written files are confined to `allowed_files`.
