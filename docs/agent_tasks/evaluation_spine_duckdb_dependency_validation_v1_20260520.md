---
job_id: evaluation_spine_duckdb_dependency_validation_v1_20260520
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520
allowed_files:
  - docs/agent_tasks/evaluation_spine_duckdb_dependency_validation_v1_20260520.md
  - docs/evaluation_spine_manifest_contract.md
  - scripts/reporting/eval_spine_ingest.py
  - scripts/reporting/test_eval_spine_ingest.py
  - scripts/reporting/test_eval_spine_manifest.py
  - scripts/reporting/requirements.txt
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/README.md
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/duckdb_smoke_summary.json
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/status.json
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/validation.json
  - reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/diff-check.json
---

# Evaluation Spine DuckDB Dependency Validation v1

Install or configure DuckDB for offline Evaluation Spine reporting/dev tooling
only, then validate the real ingest path against committed report artifacts.

## Scope

- Audit the repo dependency mechanism before adding DuckDB.
- Prefer a reporting-only dependency file for DuckDB unless repo evidence shows
  an existing dev/test dependency surface is safer.
- Use DuckDB only for offline reporting/dev Evaluation Spine ingest validation.
- Run a real offline ingest smoke into `/tmp` or `reports/eval_spine/`.
- Write a smoke summary and closeout report under the task output directory.

## Boundaries

Do not add DuckDB to backend request paths, runtime services, Docker runtime
images, production DB paths, Qdrant, news stores, memory stores,
extraction/parser routing, Cockpit chat/Home, source-label behavior,
model/GPU config, or financial truth writes.

Production data access is false. This task may read committed report artifacts
and may write a temporary DuckDB smoke database under `/tmp` or
`reports/eval_spine/`, but no `.duckdb`, `.db`, `.sqlite`, or `.sqlite3` file
may be committed unless this card is explicitly updated with justification.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_spine_duckdb_dependency_validation_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/evaluation_spine_duckdb_dependency_validation_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Evaluation/reporting dependency work
is active.

## Hard Stops

- Active registry shows overlapping Evaluation or reporting dependency work.
- Worktree has source-code dirt outside known task/report artifacts.
- Installing DuckDB would require backend runtime image, Docker Compose,
  production dependency, service startup, `.env`, or global system Python
  changes.
- Work would touch extraction/parser, Qdrant, news, memory, model/GPU, Cockpit,
  Home, source-label, or financial truth paths.
- The only way to validate would require production data access.
- The dependency manager is ambiguous and cannot be resolved safely from repo
  files.

## Validation

- `python3 scripts/reporting/eval_spine_manifest.py --help`
- `python3 scripts/reporting/eval_spine_ingest.py --help`
- Focused tests:
  `scripts/reporting/test_eval_spine_manifest.py` and
  `scripts/reporting/test_eval_spine_ingest.py`
- Build and validate manifests from committed report artifacts.
- Run a real DuckDB ingest smoke into `/tmp/tenn_eval_spine_smoke.duckdb` or a
  report-local equivalent.
- Query DuckDB to confirm expected row counts and DATA_MISSING/verdict coverage
  where the source manifests contain those records.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/evaluation_spine_duckdb_dependency_validation_v1_20260520.md`
- Verify no `.duckdb`, `.db`, `.sqlite`, or `.sqlite3` files are staged.

Do not run live extraction, Qdrant queries, news loaders, backend servers,
Cockpit chat, Home producers, runtime/model/GPU tests, memory cleanup, or
production DB reads.
