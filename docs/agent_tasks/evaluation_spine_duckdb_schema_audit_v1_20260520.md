---
job_id: evaluation_spine_duckdb_schema_audit_v1_20260520
lane: Evaluation
owner: Codex
mutation_mode: audit_only
production_data_access: false
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520
allow_audit_code_changes: true
allowed_files:
  - docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/README.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/artifact_family_inventory.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.sql
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/ingestion_manifest_contract.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/scorecard_dimension_model.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/data_missing_and_degraded_state_model.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/implementation_roadmap.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/DATA_MISSING.md
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/status.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/validation.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/diff-check.json
---

# Evaluation spine DuckDB schema audit

## Intent

Design Tenn's local evaluation spine as an offline DuckDB-first analysis layer over existing report and evaluation artifacts. The output is a report-only schema and manifest plan, with optional later MLflow tracking explicitly deferred.

## Scope

Inspect existing report, evaluation, validation, scorecard, manifest, approval, and status artifacts to determine:

- which artifact families exist;
- which artifacts are immediately machine-readable;
- which artifacts need a normalized manifest sidecar;
- how scorecards and state labels should be modeled without overclaiming canonical coverage;
- what the smallest safe follow-up implementation should be.

## Hard boundaries

Do not create a DuckDB database in a production path.
Do not add DuckDB or MLflow to backend dependencies.
Do not change evaluator, parser, source-label, Qdrant, news, memory, production DB, Cockpit chat, Home producer, runtime, model, GPU, or Financial Truth routing code.
Do not read production data.
Do not run live extraction, Qdrant queries, news loaders, chat/runtime smokes, or Home producers.
Do not mutate reports outside this task output directory.
Do not touch active A2M live trace work.

## Required outputs

- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/README.md`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/artifact_family_inventory.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.sql`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.md`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/ingestion_manifest_contract.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/scorecard_dimension_model.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/data_missing_and_degraded_state_model.md`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/implementation_roadmap.md`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/DATA_MISSING.md`

## Validation plan

- Validate this task card.
- Check registry active jobs and overlap before claiming.
- Claim only if no active job overlaps Evaluation artifact checkpointing.
- Keep A2M live trace untouched; this audit must not access live news DBs, Qdrant, or source/retrieval code.
- Validate written JSON artifacts with `jq empty`.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Release the registry claim before closeout.
