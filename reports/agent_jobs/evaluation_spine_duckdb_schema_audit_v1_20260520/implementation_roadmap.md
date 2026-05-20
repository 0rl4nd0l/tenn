# Safe Implementation Roadmap

This roadmap keeps the evaluation spine local and offline. It does not add DuckDB, MLflow, or evaluation queries to backend request paths.

## Next Task 1: Manifest Contract Generator

Add a small report-only helper that writes `manifest.json` for future reports.

Allowed scope:

- `scripts/eval_spine_manifest.py`
- focused tests for manifest generation
- one new report-only task card and report directory

Constraints:

- Do not rewrite historical reports.
- Do not read production data.
- Do not add backend dependencies.
- Do not auto-infer canonical scorecard status from prose.

Done means a future task can call the helper with job metadata and write a valid manifest sidecar.

## Next Task 2: Offline Schema Prototype Under Reports

Store the schema SQL under a report/prototype path, for example:

- `reports/eval_spine/prototype/schema.sql`
- `reports/eval_spine/prototype/README.md`

Constraints:

- No production DB path.
- No backend imports.
- No application startup hooks.
- No MLflow.

Done means the schema can be reviewed and optionally parsed by DuckDB in memory or in a disposable file under `reports/eval_spine/prototype/`.

## Next Task 3: Curated JSON Ingestion Prototype

Add one offline script that reads a tiny curated set of existing JSON artifacts:

- Gold Metric Coverage JSON
- Appendix 5B approval packet JSON
- Memory live inventory JSON
- A2M trace JSON
- `status.json`
- `diff-check.json`

Output:

- `reports/eval_spine/prototype/eval_spine.duckdb`
- `reports/eval_spine/prototype/ingestion_report.json`

Constraints:

- Reports path only.
- No production DBs.
- No Qdrant.
- No news loaders.
- No live chat/runtime smokes.
- No automatic Markdown scraping.

Done means basic queries can answer which artifacts exist, which scorecards are present, and what is missing.

## Next Task 4: Read-only CLI

Add a local CLI for offline queries such as:

- list artifact runs by lane/profile
- show scorecards by branch/HEAD
- list DATA_MISSING by family
- compare route/runtime verdicts by run

Constraints:

- CLI reads only the report-local DuckDB file.
- CLI must print profile names with every score.
- CLI must not import backend app modules.

## Next Task 5: Optional MLflow Later

Defer MLflow until the manifest and DuckDB tables are stable.

Optional future use:

- register eval runs and artifacts;
- store model/profile labels for real-gold extraction eval;
- link MLflow run IDs back to `artifact_runs`.

Do not use MLflow for canonical source of truth. DuckDB/report manifests should remain primary.

## Do Not Do

- Do not integrate DuckDB into FastAPI or Cockpit request paths.
- Do not add DuckDB to production backend dependencies.
- Do not auto-import production data.
- Do not score from sparse feedback.
- Do not replace existing report artifacts.
- Do not mutate canonical scorecards.
- Do not mix memory truth with financial truth.
- Do not infer live Qdrant/news/memory state from static code artifacts.
