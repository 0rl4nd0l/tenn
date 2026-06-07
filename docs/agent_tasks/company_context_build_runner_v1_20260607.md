---
job_id: company_context_build_runner_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/company_context_build_runner_v1_20260607.md
  - scripts/build_company_context_artifact.py
  - scripts/test_build_company_context_artifact.py
  - reports/agent_jobs/company_context_build_runner_v1_20260607/README.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/company_context_build_runner_v1_20260607
mutation_mode: controlled_artifact_provisioning
production_data_access: false
---

# Task

Add a fail-closed runner for building the production Cockpit company
qualitative-context artifact without hand-running a risky command.

# Background

PR #314 aligns Cockpit's default company DB resolution with the production
artifact root, but the production DB is still missing:

```text
/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite
```

The existing `scripts/build_qualitative_context_db.py` builder can produce the
SQLite schema and manifest, but it writes directly to its output path. A
production-ready path needs an explicit lock/temp/promote wrapper, post-build
validation, and a default mode that cannot write the production artifact.

# Required Behavior

- Default to plan/dry-run mode with no production artifact mutation.
- Require an explicit production-write flag before promotion to
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`.
- Build into a run-specific temp/staging output first.
- Validate the staged SQLite DB before promotion:
  - file exists and is non-empty,
  - `context_chunks` table exists,
  - chunk count is non-zero,
  - corpus is `company`,
  - embedding payload is present,
  - manifest exists and reports success,
  - query result count is non-zero when a query is requested.
- Use a lock file so concurrent production builds fail closed.
- Do not use hash fallback for the production semantic company DB unless an
  explicit test-only option is used.
- Preserve source PDFs, Qdrant, Redis, runtime service config, and dirty live
  checkout state.

# Hard Boundaries

- Do not build or promote the real production DB in this task.
- Do not stop `llama-server`, change GPU/runtime config, install dependencies,
  edit crontab/timers, mutate source PDFs, or write to Qdrant/Redis.
- Do not broaden Cockpit startup into degraded operation.

# Required Validation

- Run focused unit tests for argument planning, production-write gating, lock
  behavior, staged DB validation, and promotion mechanics against temp files.
- Run `git diff --check`.
- Report that no production DB was written.

# Definition Of Done

The next production artifact attempt should be executable through a reviewed,
fail-closed runner instead of an ad hoc shell command. A real production build
still requires explicit approval and compute/runtime readiness.
