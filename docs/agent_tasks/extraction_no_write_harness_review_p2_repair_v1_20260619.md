---
job_id: extraction_no_write_harness_review_p2_repair_v1_20260619
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_review_p2_repair_v1_20260619.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/README.md
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/input_manifest.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/replay_results.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/side_effect_audit.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/status.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/diff-check.json
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/PR_REVIEW.md
  - reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_no_write_harness_review_p2_repair_v1_20260619
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_review_p2_repair_v1_20260619.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_review_p2_repair_v1_20260619.md
docs_followup: NONE
reason: "The task card documents the portable manifest paths and pre-clear validation review repair."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused PR review repair for a no-write extraction safety harness."
worker_model_allowed: false
worker_decision_limit: "No workers used for this focused PR repair."
escalation_needed: false
---

# No-Write Harness P2 Review Repair

## Objective

Repair only the two PR #379 review findings explicitly approved in the current
goal:

- validate the manifest and case selector before clearing prior report
  artifacts;
- make certified guard manifest source paths portable across worktrees.

## Scope

- Update the no-write replay runner to resolve portable certified source paths
  without fetching or creating source artifacts.
- Update the certified guard manifest away from host-specific absolute source
  paths.
- Add focused tests for input validation before report reset and portable
  source-path resolution.
- Record report-local closeout artifacts for this repair.

## Hard Stops

- Do not change extraction prompts, source PDFs, gold labels, DB, Qdrant, Redis,
  news, memory, runtime/model/GPU config, dependency files, or production data.
- Do not run broad extraction, count samples, backfills, dependency installs, or
  service starts.
- Do not merge, rebase, reset, stash, clean, or delete branches/worktrees.
- GitHub mutation is limited to pushing this focused repair commit to the
  existing PR #379 branch.
- Do not address unrelated PR comments in this task.

## Validation

- Task-card validate.
- Focused no-write replay unit tests.
- `py_compile`.
- Invalid selector preservation check.
- Source-path portability check.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.
