---
job_id: a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525
title: A2M news projection audit integration and read-only smoke controller
owner: Codex
lane: Query Orchestration
primary_lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
mutation_mode: safe_extension
controller_mutation_mode: controller_safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525
allowed_files:
  - docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/diff-check.json
  - docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_readonly_smoke_matrix.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_next_fix_decision.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/diff-check.json
  - docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/news_projection_path_map.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/a2m_evidence_route_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/projection_gap_register.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/recommended_child_task_card.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/diff-check.json
---

# A2M News Projection Integration and Read-Only Smoke Controller

## Objective

Safely integrate or park the completed A2M projection-path audit commit, then run the recommended A2M read-only smoke. Create or run one bounded child safe-extension only if the smoke evidence proves that the next step is file-bounded, non-data-mutating, task-carded, and registry-safe.

## Mode

- Result review / integration for commit `3eb87220b3834ecd510202118d0c1820d7f9aa36`.
- Audit only for `a2m_news_projection_readonly_smoke_v1_20260525`.
- Safe extension only for a later exact-files child task if evidence and registry checks permit it.

## Required Scope

- Prove current canonical repo state and registry state from live commands.
- Validate task-card and registry command syntax before relying on it.
- Preserve unrelated dirty or untracked files.
- Use safe isolation before stopping on lane-only or dirty-file blockers.
- Do not claim A2M projection is fixed unless a separate validated remediation proves it.

## Forbidden

- No ingestion, backfill, reindex, resync, projection rebuild, or news refresh.
- No Qdrant mutation.
- No SQLite, Postgres, DB, news store, memory, company memory, market memory, thesis memory, or production-data mutation.
- No copying or symlinking legacy `/mnt/sdb2` DBs into canonical paths.
- No alias hacks, ticker/company canonicalization, source-label trust changes, parser changes, extraction changes, metric scoring changes, runtime reloads, Docker/systemd/cron/env edits, service starts/stops/restarts, model runtime changes, or GPU routing changes.
- No unrelated dirty-file cleanup, stash, reset, deletion, or overwrite.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md`
- Claim and release the registry job if supported and safe.
- Validate the integrated audit card if integration occurs.
- Validate all generated JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md`

## Done Criteria

- The completed A2M audit commit is integrated into canonical or explicitly parked.
- The A2M read-only smoke is complete and reported.
- The optional child safe-extension is completed only if all safety gates pass, otherwise explicitly deferred.
- No forbidden mutation occurred.
- Final report states exact branch, HEAD, registry status, changed files, validation, remaining risks, and next recommended task.
