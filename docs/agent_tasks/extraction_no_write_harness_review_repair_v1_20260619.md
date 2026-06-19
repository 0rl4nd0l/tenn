---
job_id: extraction_no_write_harness_review_repair_v1_20260619
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay/input_manifest.json
  - reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/validation.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/input_manifest.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/replay_results.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/side_effect_audit.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/docling_preflight/validation.json
  - reports/agent_jobs/extraction_docling_no_write_profile_v1_20260618/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_repair_v1_20260619/README.md
  - reports/agent_jobs/extraction_no_write_harness_review_repair_v1_20260619/status.json
  - reports/agent_jobs/extraction_no_write_harness_review_repair_v1_20260619/validation.json
  - reports/agent_jobs/extraction_no_write_harness_review_repair_v1_20260619/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_no_write_harness_review_repair_v1_20260619
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_review_repair_v1_20260619.md
docs_followup: NONE
reason: "The task card documents the secret-redaction and side-effect fail-closed review repair."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Small code-review repair touching one runner, focused tests, and report artifacts."
worker_model_allowed: false
worker_decision_limit: "No workers used for code-review repair decisions."
escalation_needed: false
---

# No-Write Harness Review Repair

## Objective

Repair the PR #379 code-review findings without widening the extraction harness
scope.

## Scope

- Redact secret-bearing environment values from committed report artifacts.
- Make replay `status` and exit code fail closed when any side-effect
  containment boolean fails.
- Add focused tests for both repairs.
- Refresh only the affected report artifacts.

## Hard Stops

- Do not change extraction prompts, source PDFs, gold labels, DB, Qdrant, Redis,
  news, memory, runtime/model/GPU config, or production data.
- Do not run broad extraction, count samples, backfills, dependency installs, or
  service starts.
- Do not merge, rebase, reset, stash, clean, or delete branches/worktrees.
- GitHub mutation is limited to pushing this repair commit to the existing draft
  PR branch.

## Validation

- Task-card validate.
- Focused no-write replay unit tests.
- `py_compile`.
- Docling no-write preflight only; expected `DATA_MISSING` if no approved
  docling venv exists.
- Secret scan over affected scripts and report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
