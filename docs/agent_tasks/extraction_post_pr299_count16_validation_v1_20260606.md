---
job_id: extraction_post_pr299_count16_validation_v1_20260606
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr299_count16_validation_v1_20260606.md
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/run_bounded_count16.py
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/run_stdout.txt
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/run_stderr.txt
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/sample_results.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/sample_manifest.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/classification.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/preflight.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/raw_commands.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606
mutation_mode: safe_extension
production_data_access: false
---

# Post PR #299 Count-16 Extraction Validation

## Objective

Run exactly one bounded count-16 extraction validation sample after PR #299 and
the post-PR299 candidate-exclusion taxonomy repair. Do not run broad
extraction, backfill, full ticker-universe extraction, count-24, or count-32.

## Commit Gate

Required baseline merge commit:
`9436d1d32de0da5423b8edcfc7efc883ccac3fd6`.

Required Phase 1 repair commit:
`9c9107bbbbac6a2971b57d9df5473aa870bb4b28`.

## Scope

Primary lane: Evaluation.

Supporting lanes: Financial Truth, Query Orchestration, Provenance.

Mode: BOUNDED VALIDATION ONLY.

Risk: MEDIUM/HIGH.

## Required Preflight

- Confirm branch/HEAD includes PR #299 and the Phase 1 repair commit.
- Confirm git status, worktrees, and registry/list-active.
- Confirm queues are clean and no unacked keys are present.
- Confirm GPU/process guard is clean or record the precise degraded state.
- Confirm source paths are available.
- Confirm llama.cpp/backend health only as needed for this direct bounded run.

## Required Run

- Use seed `20260602`, matching the prior count-16 rerun seed for comparability.
- Run exactly one count-16 sample.
- Record sample manifest: seed, candidate pool hash, selected document IDs,
  document classes, and comparability to prior count-16 if applicable.
- Classify every ok, ok_low_confidence, failed, and exception document.
- Stop after this one sample.

## Side-Effect Audit

Audit DB rows/files, Qdrant points, risk notes, news/memory, queues, and source
PDFs before and after the bounded run.

## Hard Stops

- No broad extraction/backfill.
- No full ticker-universe extraction.
- No count-24 or count-32.
- No production DB mutation beyond bounded validation route behavior.
- No Qdrant/news/memory mutation beyond bounded validation route behavior.
- No source PDF edits.
- No prompt, gold-label, runtime, or schema changes.
- No unrelated cleanup.

## Validation

- JSON validation for generated report artifacts.
- `python3 -m py_compile` for the report-local runner.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr299_count16_validation_v1_20260606.md --repo-root .`
- No source PDFs staged.
- Registry/list-active evidence.
- Final git status.
- Explicit no broad extraction/backfill/full ticker extraction statement.

## Final Report

Report ok, ok_low_confidence, failed, and exception counts; failure taxonomy;
low-confidence taxonomy; unsafe-row check; side-effect audit; whether count-24
is justified; and remaining `DATA_MISSING`.
