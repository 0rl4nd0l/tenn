---
job_id: company_context_provisioning_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - AGENTS.md
  - docs/agent_tasks/company_context_provisioning_v1_20260607.md
  - financial-engine_v2/cockpit/core/config.py
  - financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py
  - financial-engine_v2/cockpit/ui/app.py
  - financial-engine_v2/scripts/test_cockpit_company_context_path.py
  - reports/agent_jobs/company_context_provisioning_v1_20260607/README.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/company_context_provisioning_v1_20260607
mutation_mode: controlled_artifact_provisioning
production_data_access: true
---

# Task

Remediate the missing Cockpit company qualitative-context DB as a production
readiness issue, without hiding the missing artifact behind degraded operation.

# Background

After PR #313 aligned Cockpit news context resolution with nightly artifacts,
the usual Cockpit runtime no longer reaches the news reader because startup
fails earlier on the required company qualitative-context DB:

```text
reports/qual_context/company.sqlite
```

Current evidence shows `reports/` is ignored, the DBs are generated artifacts,
and the active checkout has no company context DB. The NVMe artifact/source tree
contains ASX PDFs, but no `company.sqlite` or canonical company aliases.

# Required Behavior

- Treat the company qualitative-context DB as a required production artifact.
- Do not change Cockpit to silently degrade past a missing required company DB.
- Align company DB resolution with the production artifact root, preserving
  explicit absolute paths and allowing explicit Cockpit/company env overrides.
- Document that safe-installable missing dependencies should be installed in the
  project/runtime venv rather than hidden behind degraded behavior.
- Validate the company DB builder against temporary artifacts before any live
  production artifact write.
- If live artifact provisioning is performed, build into the resolved production
  artifact root and verify schema/content enough for Cockpit startup.
- Preserve the dirty live checkout and unrelated ignored runtime artifacts.

# Hard Boundaries

- Do not edit crontab, timers, Docker runtime config, host env files, symlinks,
  source PDFs, extraction prompts, gold labels, parser routing, model/GPU config,
  or migrations.
- Do not mutate Qdrant, Redis, memory stores, source PDFs, or extraction truth
  data.
- Do not copy stale DB artifacts to satisfy startup.
- Do not remove, clean, or overwrite unrelated dirty/untracked files.
- Do not use degraded-startup behavior as the remediation.

# Required Validation

- Validate this task card with Tenn tooling when available; otherwise record
  `DATA_MISSING`.
- Inventory expected DB paths and actual filesystem artifacts.
- Run a temp-artifact build from a bounded local source slice to prove builder
  dependencies, schema, and query path.
- If a live company DB is built, verify:
  - DB exists at the intended production artifact root,
  - expected tables exist,
  - row/chunk counts are non-zero,
  - a representative query returns rows,
  - Cockpit startup progresses past company DB validation.
- Run `git diff --check` for tracked changes.

# Definition Of Done

Production readiness is improved only if the missing company DB root cause is
made more true: either a valid company context DB is provisioned and startup is
verified, or a precise blocker remains with evidence showing what prevents safe
provisioning.
