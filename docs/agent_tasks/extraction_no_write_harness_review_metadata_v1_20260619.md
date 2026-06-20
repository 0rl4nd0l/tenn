---
job_id: extraction_no_write_harness_review_metadata_v1_20260619
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_review_metadata_v1_20260619.md
  - docs/agent_tasks/extraction_no_write_replay_harness_v1_20260618.md
  - docs/agent_tasks/extraction_docling_no_write_profile_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_publish_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
  - reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619/README.md
  - reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619/status.json
  - reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619/diff-check.json
  - reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619/PR_REVIEW.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/extraction_no_write_harness_review_metadata_v1_20260619
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_replay_harness_v1_20260618.md
  - docs/agent_tasks/extraction_docling_no_write_profile_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_publish_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_replay_harness_v1_20260618.md
  - docs/agent_tasks/extraction_docling_no_write_profile_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_publish_v1_20260618.md
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
docs_followup: NONE
reason: "Records docs-impact and model-routing metadata required by the current Tenn review gate."
task_tier: small
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Small metadata-only PR repair after green harness validation."
worker_model_allowed: false
worker_decision_limit: "No workers used."
escalation_needed: false
---

# No-Write Harness Review Metadata Repair

## Objective

Add explicit Docs Impact and Model/Worker Routing metadata to the PR #379 task
cards, then repeat the PR review.

## Scope

- Update task-card metadata only.
- Add a report-local validation and review bundle.
- Push this metadata-only repair to the existing PR branch.

## Hard Stops

- Do not change harness code, tests, manifest cases, extraction logic, source
  PDFs, prompts, gold labels, DB, Qdrant, Redis, news, memory, runtime/model/GPU
  config, production data, venvs, or dependency files.
- Do not run broad extraction, count samples, backfills, dependency installs, or
  service starts.
- Do not merge, rebase, reset, stash, clean, or delete branches/worktrees.

## Validation

- Task-card validate.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.
- Repeat read-only PR review.
