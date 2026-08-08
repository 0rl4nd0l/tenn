---
job_id: news_ingestion_throughput_profile_and_optimise_v1_20260527
lane: Evaluation
supporting_lanes:
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/news_ingestion_throughput_profile_and_optimise_v1_20260527.md
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/README.md
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/profile_matrix.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/status.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/validation.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/diff-check.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/bash_nightly_news.txt
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/fetch_dry_run.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/fetch_dry_run_time.txt
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_dry_run_summary.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_dry_run_stdout.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_dry_run_time.txt
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_full_dry_run_summary.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_full_dry_run_stdout.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/load_full_dry_run_time.txt
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/sqlite_fallback_scratch_profile.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/memo_dispatch_plan.json
  - reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527/retention_candidates.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_ingestion_throughput_profile_and_optimise_v1_20260527
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 123
---

# News Ingestion Throughput Profile

## Objective

Produce a no-write profile and bottleneck map for the nightly news ingestion
path without mutating production DB, Qdrant, news, memory, runtime, or scheduler
state.

## Scope

Allowed writes are limited to this task card and the report bundle. Temporary
SQLite/log artifacts may be created under `/tmp` only and must not be committed.
Committed reports must redact host-local absolute paths.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_ingestion_throughput_profile_and_optimise_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_ingestion_throughput_profile_and_optimise_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/news_ingestion_throughput_profile_and_optimise_v1_20260527.md --repo-root .`
- `bash -n financial-engine_v2/scripts/nightly_news.sh`
- no-write fetch dry-run using `/tmp` output paths
- no-write loader dry-run using a `/tmp` copied SQLite artifact if available
- JSON validation for generated reports
- `git diff --check`
- task-card `check-diff`
- registry release before closeout

## Hard Stops

- Any command would write production DB/Qdrant/news/memory stores.
- Live fetch, live sync, memo dispatch, cleanup, scheduler, model/runtime/GPU,
  or service config mutation is required.
- Required venvs are unavailable in the isolated worktree and cannot be used
  read-only from an existing checkout.
- Active job overlap appears on allowed files.
