# Evaluation Spine Manifest Foundation v1

Job: `evaluation_spine_manifest_foundation_v1_20260520`
Lane: Evaluation
Supporting lanes: Reporting, Provenance
Mode: SAFE EXTENSION
Production data access: false

## Confirmed Facts

- Runtime checkout: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Starting HEAD: `fa776ce93f99`.
- Initial worktree status was clean.
- The task card validated successfully.
- Shared registry had no active jobs or overlap before claim.
- Registry claim succeeded for this job.
- Evaluation Spine audit artifacts were absent from the active branch and were checkpointed from `/home/l4nd0/tenn-evaluation-spine-duckdb-audit-v1-20260520`.
- No backend request path, extraction/parser code, Qdrant/news/memory store, runtime/model/GPU config, Cockpit chat/Home path, source-label logic, production DB, or financial truth writer was touched.

## Inferred Facts

- The copied audit bundle was uncommitted/ignored in the isolated audit worktree, so this task needed an artifact checkpoint.
- The manifest generator can normalize future task/report metadata without scraping large Markdown bodies.
- The DuckDB ingestion prototype is shape proof only; because `duckdb` is unavailable in the current system Python, no DuckDB database was created in this checkout.

## DATA_MISSING

- Final commit hash cannot be embedded in the committed report without becoming self-referential; it is reported in the final closeout.
- DuckDB execution path was not run because the `duckdb` Python package is unavailable in the current environment.
- Broad historical Markdown-only report normalization remains deferred to future jobs.
- MLflow remains deferred.

## Files Added

- `docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md`
- `docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md`
- `docs/evaluation_spine_manifest_contract.md`
- `scripts/reporting/eval_spine_manifest.py`
- `scripts/reporting/eval_spine_ingest.py`
- `scripts/reporting/eval_spine_schema.sql`
- `scripts/reporting/test_eval_spine_manifest.py`
- `scripts/reporting/test_eval_spine_ingest.py`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/*`
- `reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/README.md`
- `reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/status.json`
- `reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/validation.json`
- `reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/diff-check.json`
- `reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/manifest.json`

## Manifest Contract Summary

- Required fields include job/run identity, branch/head/worktree, task card, output dir, status, verdicts, scorecards, validation commands, changed files, DATA_MISSING, degraded states, source artifacts, save recommendation, and do-not-overclaim guards.
- Missing evidence is represented through `data_missing[]`; the generator does not invent unresolved branch, commit, runtime, status, or save fields.
- Scorecard rows require `scorecard_profile`.
- `canonical_core` is guarded against being presented as broad production extraction coverage.
- Expected 404 and expected empty states are representable as non-failure degraded states.

## Schema Summary

`scripts/reporting/eval_spine_schema.sql` defines offline DuckDB tables for run envelopes, task cards, validation commands, artifact files, scorecards, metric expectations/results, runtime smokes, route smokes, source-label checks, memory audit results, news traces, dirty worktree events, registry events, DATA_MISSING items, and decisions/verdicts.

## Ingest Prototype Summary

- `scripts/reporting/eval_spine_ingest.py` accepts explicit JSON inputs and an explicit `--db` path only under `reports/eval_spine/` or `/tmp`.
- It refuses unsafe DB paths before importing DuckDB.
- It exits gracefully with code `2` when the `duckdb` Python package is unavailable.
- It does not import backend modules or read production stores.

## Tests Run And Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md`: ok.
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`: ok, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`: ok.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`: ok.
- `uv run --with pytest python -m pytest scripts/reporting/test_eval_spine_manifest.py scripts/reporting/test_eval_spine_ingest.py`: 9 passed, 1 skipped, 1 warning.
- `python3 -m compileall scripts/reporting`: ok.
- `python3 scripts/reporting/eval_spine_manifest.py --help`: ok.
- `python3 scripts/reporting/eval_spine_ingest.py --help`: ok.
- `python3 scripts/reporting/eval_spine_manifest.py build --task-card docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md --report-dir reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520 --out /tmp/evaluation_spine_audit_manifest.json`: ok.
- `python3 scripts/reporting/eval_spine_manifest.py validate /tmp/evaluation_spine_audit_manifest.json`: ok.
- `python3 scripts/reporting/eval_spine_manifest.py build --task-card docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md --report-dir reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520 --out reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/manifest.json`: ok.
- `python3 scripts/reporting/eval_spine_manifest.py validate reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520/manifest.json`: ok.
- `python3 scripts/reporting/eval_spine_ingest.py --db /tmp/evaluation_spine_audit.duckdb /tmp/evaluation_spine_audit_manifest.json`: exited 2 with graceful missing-DuckDB message.
- `python3 scripts/reporting/eval_spine_ingest.py --db unsafe.duckdb /tmp/evaluation_spine_audit_manifest.json`: exited 1 with unsafe-path refusal.
- `git diff --check`: ok.
- `git diff --cached --check`: ok.
- Final task-card `check-diff`: recorded in `diff-check.json`.

## DuckDB Availability Result

`python3 -c "import duckdb; print(duckdb.__version__)"` failed with `ModuleNotFoundError: No module named 'duckdb'`.

## Safety Boundary Confirmation

This task read committed or checkpointed report artifacts and synthetic/temp manifest outputs only. It did not access production data, Qdrant, news stores, memory stores, runtime services, model/GPU paths, Cockpit chat/Home, backend request paths, extraction/parser routing, source-label logic, or financial truth write paths.

## Source Artifacts Used For Sample Manifest

- `docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/status.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/diff-check.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/validation.json`
- `reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/README.md`

## Final Git And Registry Status

- Final git status: reported in the final closeout after commit.
- Registry release status: released; final `list-active` returned `active_jobs: []`.
- Commit hash: reported in the final closeout after commit.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: save the offline Evaluation Spine manifest/schema/ingest foundation pattern, especially the DATA_MISSING and do-not-overclaim contract.
