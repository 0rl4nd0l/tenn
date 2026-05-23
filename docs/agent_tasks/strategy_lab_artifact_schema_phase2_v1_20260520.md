---
job_id: strategy_lab_artifact_schema_phase2_v1_20260520
lane: Provenance
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520
allowed_files:
  - docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md
  - docs/strategy_lab/**
  - docs/strategy_lab/artifact_schema_v1.md
  - docs/strategy_lab/artifact_schema_v1.schema.json
  - docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json
  - docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json
  - docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json
  - docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/**
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/phase1_payload_mapping.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/schema_invariants.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/validation_notes.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/go_no_go_phase3.md
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/diff-check.json
---

# Task

Run Phase 2 Strategy Lab artifact schema-only design for QuantDinger/Tenn using the completed Phase 1 isolated sandbox evidence.

Mode: SCHEMA-ONLY SAFE EXTENSION / REPORT + DOCS ONLY.

Primary lane: Provenance.

Supporting lanes:

- Evaluation.
- Query Orchestration.
- Reporting.

# Architecture Boundary

- Tenn is the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator only.
- QuantDinger outputs become Strategy Lab artifacts, never canonical financial truth.
- Strategy Lab artifacts default to `PENDING_REVIEW`.
- No Strategy Lab artifact may affect memory, watchlist priority, company analysis, thesis state, holdings, or financial truth without later human review and a separately approved task card.
- Codex is a dev/audit agent only, not the runtime path.

# Allowed Writes

- This task card.
- `docs/strategy_lab/**`.
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/**`.

If `docs/strategy_lab/**` overlaps dirty or claimed work, stop and report the collision rather than improvising.

# Forbidden Writes

- Tenn runtime/product code.
- Cockpit UI/backend code.
- DB, Qdrant, news, memory, or financial-truth stores.
- Parser, extraction, or gold-label files.
- Source-registry writes.
- Docker, systemd, env, or secrets files.
- QuantDinger install/runtime directories.
- MCP adapter/client implementation.
- Broker, exchange, paper, or live execution configs.
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

# Phase 1 Inputs

Inspect the Phase 1 report bundle at:

- `/home/l4nd0/tenn-strategy-lab-quantdinger-phase1-sandbox-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520/`

Inspect prior framework/schema docs and Phase 0 fit report if present. If any input path is unavailable, mark it `DATA_MISSING` and continue only if the remaining evidence is enough to define a provisional schema.

# Scope

Define Strategy Lab artifact envelope v1, allowed artifact types, safety/truth flags, evidence labels, forbidden labels, Phase 1 payload mapping, review workflow, schema invariants, valid/invalid JSON fixtures, and a future offline validator contract.

Do not implement runtime validation, artifact storage, adapter code, Cockpit UI/backend wiring, Tenn runtime code, store writes, QuantDinger startup, token issuance, or paper/live execution.

# Required Outputs

- `docs/strategy_lab/artifact_schema_v1.md`
- `docs/strategy_lab/artifact_schema_v1.schema.json`
- `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/phase1_payload_mapping.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/schema_invariants.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/validation_notes.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/go_no_go_phase3.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/status.json`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/diff-check.json` if supported.

# Validation

Run and report:

- Task-card validation if supported.
- Registry `list-active`, `check-overlap`, claim, release, and final `list-active` if supported.
- JSON parse validation for schema and all JSON fixtures.
- Markdown/doc sanity check if repo has one.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md` if supported.
- Final `git status --short --untracked-files=all`.

Prove all written files are inside allowed paths and no runtime/product code, production data, Tenn stores, services, tokens, or paper/live execution were touched.

# Go/No-Go

Recommend exactly one:

- `GO_PHASE3_MOCKED_ADAPTER_DESIGN_ONLY`
- `DEFER_SCHEMA_REVIEW_REQUIRED`
- `DEFER_NEEDS_MORE_PHASE1_PAYLOAD_EVIDENCE`
- `REJECT_TOO_RISKY`
