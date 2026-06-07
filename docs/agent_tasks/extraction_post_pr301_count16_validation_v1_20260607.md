---
job_id: extraction_post_pr301_count16_validation_v1_20260607
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr301_count16_validation_v1_20260607.md
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/run_bounded_count16.py
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/run_stdout.txt
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/run_stderr.txt
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/sample_results.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/sample_manifest.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/classification.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/preflight.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/raw_commands.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR301 Count-16 Extraction Validation

## Objective

Run exactly one bounded count-16 extraction validation sample after DXC/LBL
containment proof and candidate-exclusion hardening. Do not run count-24,
count-32, broad extraction, broad backfill, full ticker-universe extraction, or
random repeated samples.

## Scope

Primary lane: Evaluation.

Supporting lanes: Financial Truth, Query Orchestration, Provenance, Repo
Hygiene.

Mode: BOUNDED VALIDATION ONLY.

Risk: HIGH.

## Required Preflight

- Confirm branch/HEAD includes PR #301 and previous post-PR301 milestones.
- Confirm git status, worktrees, and registry active-record evidence.
- Confirm queues are clean and no unacked keys are present.
- Confirm GPU/process guard is clean or record precise degraded state.
- Confirm source paths are available.
- Confirm backend health if needed.
- Confirm loaded commit proof if available; otherwise record `DATA_MISSING`.

## Required Run

- Run exactly one count-16 sample.
- Record seed, candidate pool hash, selected document IDs, document classes, and
  comparison to prior count-16 if comparable.
- Classify ok, ok_low_confidence, failed, and exception counts.
- Report failure taxonomy, low-confidence taxonomy, and accepted-output risk
  audit.
- Stop after this one sample.

## Side-Effect Audit

Audit DB rows, Qdrant points, risk notes, news/memory, queues, and source PDFs
before and after the bounded run.

## Hard Stops

- No broad extraction/backfill.
- No full ticker-universe extraction.
- No count-24 or count-32.
- No repeated random samples beyond this single count-16 phase.
- No production DB mutation beyond bounded validation route behavior.
- No Qdrant/news/memory mutation beyond bounded validation route behavior.
- No source PDF edits.
- No prompt, gold-label, runtime, model, GPU, or schema changes.
- No unrelated cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr301_count16_validation_v1_20260607.md`
- JSON validation for generated report artifacts.
- `python3 -m py_compile` for the report-local runner.
- `git diff --check`.
- `git diff --cached --check` if staging.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr301_count16_validation_v1_20260607.md --repo-root .`
- Verify no source PDFs are staged.
- Registry active-record evidence.
- Final git status.
- Explicit no broad extraction/backfill/full ticker extraction statement.

## Final Report

Report ok, ok_low_confidence, failed, and exception counts; failure taxonomy;
low-confidence taxonomy; accepted-output risk audit; side-effect audit; whether
count-24 is justified; and remaining `DATA_MISSING`.
