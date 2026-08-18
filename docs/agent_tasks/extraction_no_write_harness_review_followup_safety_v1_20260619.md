---
job_id: extraction_no_write_harness_review_followup_safety_v1_20260619
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_review_followup_safety_v1_20260619.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/README.md
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/status.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/diff-check.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/PR_REVIEW.md
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/baseline_preflight/input_manifest.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/baseline_preflight/replay_results.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/baseline_preflight/side_effect_audit.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/baseline_preflight/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619/baseline_preflight/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_no_write_harness_review_followup_safety_v1_20260619
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_review_followup_safety_v1_20260619.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_review_followup_safety_v1_20260619.md
docs_followup: NONE
reason: "The task card records the PR #379 no-write safety review follow-up scope."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused PR review safety repair for the certified no-write extraction replay harness."
worker_model_allowed: false
worker_decision_limit: "Workers are already report-only for board lanes; this code integration is orchestrator-owned."
escalation_needed: false
---

# No-Write Harness Review Follow-Up Safety

## Objective

Address the fresh PR #379 no-write harness safety review comments that surfaced
after the portable-path and pre-clear-validation repair:

- detect writes to repo files that were already dirty before replay;
- snapshot whole normal parser cache roots rather than predicted cache files
  only;
- fail unexpected per-case extraction exceptions instead of reporting them as
  missing infrastructure;
- force strict docling semantics for the `docling-no-write` profile;
- preserve read-only source-root `DATA_ROOT` and `DOCS_ROOT` through docling
  profile re-exec.

## Scope

- Update only `scripts/extraction_no_write_replay.py` and focused unit tests.
- Record report-local validation and review artifacts.
- Push only this focused follow-up to PR #379 if validation passes.

## Hard Stops

- Do not run broad extraction, count-24/count-32, random sampling, backfills,
  full-universe extraction, services, DB, Qdrant, Redis, news, memory, source
  PDF, prompt, gold-label, schema, runtime, model, GPU, or production-data
  mutation.
- Do not merge, rebase, cherry-pick, reset, stash, clean, or delete branches or
  worktrees.
- Do not mutate unrelated GitHub PRs/issues.
- Do not address unrelated extraction behavior outside the no-write harness.

## Validation

- Task-card validate.
- Focused no-write replay unit tests.
- `py_compile`.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Report artifact check.
