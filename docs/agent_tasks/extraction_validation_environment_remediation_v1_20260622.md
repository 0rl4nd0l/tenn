---
job_id: extraction_validation_environment_remediation_v1_20260622
lane: Evaluation
supporting_lanes:
  - Reporting
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_validation_environment_remediation_v1_20260622.md
  - docs/validation_baseline.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - scripts/run_pytest_with_fallback.py
  - scripts/test_run_pytest_with_fallback.py
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/TASK_CARD.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/BOARD.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/BOARD_DECISION.json
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/STATE.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/DECISIONS.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/CODE_REVIEW.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/NEXT_GOAL.md
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/status.json
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/validation.json
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/diff-check.json
  - reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622/pytest_fallback_selftest.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_validation_environment_remediation_v1_20260622
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/validation_baseline.md
  - scripts/extraction_no_write_replay.py
  - scripts/run_pytest_with_fallback.py
docs_changed:
  - docs/validation_baseline.md
docs_followup: NONE
reason: "Remediate the validation-environment failure that left focused pytest unavailable and broad no-write replays able to hang without structured artifacts."
task_tier: large
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "The remediation changes validation control-plane behavior for Financial Truth extraction closeout and must preserve no-write safety."
worker_model_allowed: false
worker_decision_limit: "No worker delegation; orchestrator owns review-board decision, implementation, validation, and PR update."
escalation_needed: false
---

# Extraction Validation Environment Remediation

## Objective

Make the validation failure mode from the metric-improvement sprint hard to
repeat:

- Focused pytest must have one repo-native command that can use an existing
  runtime venv without mutating it and add pytest only in an ephemeral overlay.
- Certified no-write replays must have a per-case timeout that produces
  structured report artifacts instead of hanging indefinitely in Docling or LLM
  calls.

## Hard Stops

- Do not mutate production data, DB, Qdrant, Redis, news, runtime services,
  source PDFs, gold labels, prompts, or model files.
- Do not change project dependency lockfiles, CI config, runtime venvs,
  host-global config, or system packages.
- Do not broaden extraction semantics or replay manifest certification.
- Do not merge, rebase, reset, stash, clean, force-push, delete branches, or
  remove worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_validation_environment_remediation_v1_20260622.md`
- `python3 scripts/test_run_pytest_with_fallback.py`
- `python3 scripts/run_pytest_with_fallback.py --base-python "$(command -v python3)" -- scripts/test_run_pytest_with_fallback.py -q`
- `python3 scripts/test_extraction_no_write_replay.py`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_validation_environment_remediation_v1_20260622.md`
- `git diff --check`

## Done

- Review board records root cause, minority objections, and actionable decision.
- The pytest fallback path is executable and documented.
- No-write replay timeout behavior is unit-tested and defaults to a bounded
  timeout.
- Report bundle and code review are committed and pushed to the existing draft
  PR branch.
