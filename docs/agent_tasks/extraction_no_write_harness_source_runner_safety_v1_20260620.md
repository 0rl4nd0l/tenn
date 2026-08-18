---
job_id: extraction_no_write_harness_source_runner_safety_v1_20260620
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_source_runner_safety_v1_20260620.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/README.md
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/PR_REVIEW.md
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/status.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/validation.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/diff-check.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/baseline_preflight/input_manifest.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/baseline_preflight/replay_results.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/baseline_preflight/side_effect_audit.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/baseline_preflight/validation.json
  - reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620/baseline_preflight/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_no_write_harness_source_runner_safety_v1_20260620
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_source_runner_safety_v1_20260620.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_source_runner_safety_v1_20260620.md
docs_followup: NONE
reason: "The task card documents the source-directory side-effect audit and runner exception classification PR repair."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused PR review repair for a no-write extraction safety harness."
worker_model_allowed: false
worker_decision_limit: "No workers used for this focused PR repair."
escalation_needed: false
---

# No-Write Harness Source and Runner Safety Repair

## Objective

Repair only the two current PR #379 review findings:

- snapshot source directories so sidecar writes next to source PDFs are detected;
- classify top-level runner exceptions before reporting `DATA_MISSING`.

## Scope

- Update `scripts/extraction_no_write_replay.py` to audit source directories
  around selected PDF sources.
- Add a focused runner exception classification helper so infrastructure
  failures can remain `DATA_MISSING` while unexpected runner bugs fail.
- Add regression tests for both review findings.
- Record report-local validation and review artifacts for this repair.

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
- Baseline preflight-only no-write harness run.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.
- Local code review.
