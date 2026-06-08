---
job_id: health_snapshot_artifact_paths_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/health_snapshot_artifact_paths_v1_20260607.md
  - scripts/generate_engine_health_snapshot.py
  - scripts/test_generate_engine_health_snapshot.py
  - reports/agent_jobs/health_snapshot_artifact_paths_v1_20260607/README.md
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/health_snapshot_artifact_paths_v1_20260607
mutation_mode: code_and_report_only
production_data_access: false
---

# Task

Align the research-engine health snapshot default news/company context DB paths
with the production qualitative-context artifact root.

# Background

Nightly news and Cockpit now use generated artifacts under:

```text
/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context
```

However `scripts/generate_engine_health_snapshot.py` still defaults to
repo-local:

```text
reports/qual_context/news.sqlite
reports/qual_context/company.sqlite
```

That can make health gates inspect stale or missing repo-local artifacts rather
than the production artifacts Cockpit is expected to use.

# Required Behavior

- Default news/company health snapshot DB paths to the production artifact root.
- Preserve explicit CLI path overrides.
- Respect the same env override families used by Cockpit/news routing:
  `COCKPIT_NEWS_DB_PATH`, `TENN_NEWS_CONTEXT_DB`, `TENN_NEWS_ARTIFACT_ROOT`,
  `COCKPIT_COMPANY_DB_PATH`, `TENN_COMPANY_CONTEXT_DB`, and
  `TENN_QUAL_CONTEXT_ARTIFACT_ROOT`.
- Do not create degraded success behavior: missing DBs should remain visible in
  the health snapshot.
- Treat the default `news` corpus as the news family, including provider-specific
  corpora such as `news_newspaper4k`, while preserving exact matching for
  explicit non-default corpus filters.
- Do not write or copy DB artifacts.

# Hard Boundaries

- Do not mutate `/mnt/tenn-nvme2/.../company.sqlite`, Qdrant, Redis, source
  PDFs, runtime service config, crontab/timers, Docker config, or the dirty live
  checkout.
- Do not merge or close PRs.

# Required Validation

- Add focused tests for default artifact-root path resolution and env override
  priority.
- Run the existing health snapshot tests.
- Run `git diff --check`.
- Report that no DB artifact was written.

# Definition Of Done

The health snapshot default path contract matches the production artifact root
and can no longer silently prefer stale repo-local context DBs unless an
operator supplies an explicit CLI path.
