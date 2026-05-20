---
job_id: evaluation_spine_manifest_foundation_v1_20260520
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520
allowed_files:
  - docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md
  - docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md
  - docs/evaluation_spine_manifest_contract.md
  - scripts/reporting/eval_spine_manifest.py
  - scripts/reporting/eval_spine_ingest.py
  - scripts/reporting/eval_spine_schema.sql
  - scripts/reporting/test_eval_spine_manifest.py
  - scripts/reporting/test_eval_spine_ingest.py
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
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/validation.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/diff-check.json
  - reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/status.json
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/README.md
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/status.json
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/validation.json
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/diff-check.json
  - reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/manifest.json
---

# Evaluation Spine Manifest Foundation v1

Implement an offline-only evaluation/reporting spine foundation from the completed
Evaluation Spine DuckDB Schema Audit.

## Scope

- Checkpoint the Evaluation Spine audit task and report artifacts if they are not
  already preserved on this branch.
- Add a future report manifest contract.
- Add a standard-library manifest generator and validator.
- Add offline-only DuckDB schema SQL and a curated ingestion prototype.
- Add focused tests for offline boundaries, DATA_MISSING preservation, scorecard
  semantics, and ingestion path safety.

## Boundaries

Do not touch backend request paths, production DBs, Qdrant, news stores, memory
stores, extraction/parser routing, Cockpit chat/Home/runtime, source-label logic,
model/GPU config, or financial truth writes.

Production data access is false. This task may read committed report artifacts
and synthetic temporary fixtures only.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Evaluation/reporting work is active.

## Hard Stops

- Active registry shows overlapping Evaluation or reporting work.
- Worktree has source-code dirt outside known task/report artifacts.
- Implementation would require production data access.
- Implementation would touch backend app request paths, extraction/parser code,
  Qdrant, news stores, memory stores, production DBs, runtime, Home, Cockpit
  chat, source labels, or model/GPU config.
- DuckDB cannot be used without adding a backend dependency.
- Tests cannot run and no safe fallback validation exists.

## Validation

- Focused tests for `scripts/reporting/test_eval_spine_manifest.py` and
  `scripts/reporting/test_eval_spine_ingest.py`.
- `python3 scripts/reporting/eval_spine_manifest.py --help`
- `python3 scripts/reporting/eval_spine_ingest.py --help`
- Build and validate a sample manifest from a committed or synthetic report.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md`

Do not run live extraction, Qdrant queries, news loaders, backend server,
Cockpit chat, Home producers, runtime/model/GPU tests, memory cleanup, or
production DB reads.
