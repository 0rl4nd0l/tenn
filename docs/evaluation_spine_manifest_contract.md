# Evaluation Spine Report Manifest Contract

The Evaluation Spine manifest is additive metadata for future Tenn report and
evaluation jobs. It lives beside a report as `manifest.json` and must not alter
source reports, task cards, production stores, Qdrant, memory stores, news
stores, or backend request paths.

## Required Fields

- `job_id`: task-card job ID.
- `lane`: primary lane.
- `supporting_lanes`: secondary lanes, or an empty list.
- `mode`: task mutation mode such as `audit_only`, `safe_extension`, `blocked`,
  or `design_only`.
- `production_data_access`: boolean. Access to production data must be explicit
  and scoped.
- `branch`: source branch, or `null` with a `data_missing` row.
- `head`: source commit, or `null` with a `data_missing` row.
- `base_head`: comparison base commit, or `null` with a `data_missing` row.
- `worktree`: source worktree, or `null` with a `data_missing` row.
- `task_card`: object with `path`, `sha256`, `validation_ok`, and optional
  `validation_issues`, or `null` with a `data_missing` row.
- `output_dir`: report directory.
- `started_at`: ISO timestamp, or `null` with a `data_missing` row.
- `completed_at`: ISO timestamp, or `null` with a `data_missing` row.
- `status`: report/job status, or `null` with a `data_missing` row.
- `verdicts`: list of typed verdict rows.
- `scorecards`: list of scorecard rows. Every row must name
  `scorecard_profile`.
- `validation_commands`: list of command/result rows.
- `changed_files`: list of changed-file rows.
- `data_missing`: list of missing-evidence rows.
- `degraded_states`: list of expected or degraded state rows.
- `source_artifacts`: list of source artifact references with path and optional
  hash.
- `save_recommendation`: one of `SAVE_RECOMMENDED`, `NO_SAVE_NEEDED`,
  `SAVE_DEFERRED`, or `DATA_MISSING`, or `null` with a `data_missing` row.
- `do_not_overclaim`: list of guardrails that constrain interpretation.

## Semantics

- Missing evidence must be represented as `data_missing[]`; do not invent
  branch, commit, runtime, validation, score, or source values.
- Scorecard rows must include `scorecard_profile`. `canonical_core`,
  `expanded_required`, `confirmed_metric_coverage`, runtime smoke, route parity,
  source-label, memory, news trace, UI honesty, and feedback-quality profiles
  must not be collapsed into a single unnamed pass rate.
- `canonical_core` is a strict no-regression profile only. It must not be
  presented as broad production extraction coverage.
- Expected `404` routes and expected empty states must be represented as expected
  states, not failures.
- Direct runtime stability must not imply Cockpit route or chat stability.
- Memory context must not become financial truth.
- Production-data access must be explicit and scoped. Static report ingestion
  should keep `production_data_access: false`.
- Source artifacts remain authoritative. The manifest is an index and
  normalization sidecar, not a rewrite of the report.

## Offline DuckDB Ingest

The optional DuckDB ingest path is for offline reporting/dev validation only.
Install its dependency from `scripts/reporting/requirements.txt` or run it with
an ephemeral tool environment such as:

```bash
uv run --with duckdb --with pytest python -m pytest scripts/reporting/test_eval_spine_ingest.py -q
```

Do not add DuckDB to backend runtime requirements, Docker images, service
startup, production database paths, Qdrant, news stores, memory stores,
extraction/parser routing, Cockpit surfaces, or financial truth writes.

## Minimal Example

```json
{
  "job_id": "example_eval_job",
  "lane": "Evaluation",
  "supporting_lanes": ["Reporting"],
  "mode": "safe_extension",
  "production_data_access": false,
  "branch": "safe/example",
  "head": "abc123def456",
  "base_head": null,
  "worktree": "/home/l4nd0/tenn-example",
  "task_card": {
    "path": "docs/agent_tasks/example_eval_job.md",
    "sha256": "sha256...",
    "validation_ok": true,
    "validation_issues": []
  },
  "output_dir": "reports/agent_jobs/example_eval_job",
  "started_at": "2026-05-20T00:00:00Z",
  "completed_at": "2026-05-20T00:05:00Z",
  "status": "complete",
  "verdicts": [],
  "scorecards": [
    {
      "scorecard_profile": "canonical_core",
      "status": "passed",
      "overclaim_guard": "canonical_core is not broad production extraction coverage"
    }
  ],
  "validation_commands": [],
  "changed_files": [],
  "data_missing": [
    {
      "field": "base_head",
      "code": "missing_base_head",
      "description": "No comparison base was recorded.",
      "source_artifact": "manifest_generator"
    }
  ],
  "degraded_states": [
    {
      "classification": "expected_404",
      "route_path": "/api/example/absent",
      "is_failure": false
    }
  ],
  "source_artifacts": [],
  "save_recommendation": "SAVE_DEFERRED",
  "do_not_overclaim": [
    "canonical_core must not be presented as broad production extraction coverage",
    "Direct runtime stability must not imply Cockpit route stability",
    "Memory context must not become financial truth"
  ]
}
```
