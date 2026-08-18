---
job_id: extraction_post_pr297_failure_taxonomy_v1_20260605
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr297_failure_taxonomy_v1_20260605.md
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/README.md
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/failure_taxonomy.json
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/source_evidence.json
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/root_cause_analysis.json
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/status.json
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/validation.json
  - reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605/diff-check.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/README.md
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/classification.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/diff-check.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/preflight.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/run_bounded_count16.py
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/run_stderr.txt
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/run_stdout.txt
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/sample_manifest.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/sample_results.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/side_effect_audit.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/status.json
  - reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/validation.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_post_pr297_failure_taxonomy_v1_20260605
mutation_mode: safe_extension
production_data_access: false
---

# Post PR #297 Failure Taxonomy Audit

## Objective

Audit the thirteen failed documents from the post-PR297 count-16 validation and
identify the next narrow source-bound extraction repairs. Do not rerun the
sample, run broad extraction, run backfill, restart services, or mutate runtime
stores.

## Scope

Primary lane: Financial Truth.

Supporting lanes: Evaluation, Query Orchestration, Provenance.

Mode: AUDIT FIRST; SAFE EXTENSION only if narrow, source-bound, and tested.

Risk: MEDIUM/HIGH.

## Source Artifact

Use the preserved count-16 validation artifacts under
`reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/`.

Observed summary:

- `ok=3`
- `ok_low_confidence=0`
- `failed=13`
- `exceptions=0`

Failure taxonomy:

- `validation_gate:scale_unknown=7`
- `validation_gate:scale_validation=2`
- `classifier_low_confidence:0.0=3`
- `classifier_low_confidence:0.2=1`

## Required Audit

- List each failed document, ticker, title, source path, and failure gate.
- Split failures into:
  - true noncandidate docs;
  - eligible financial docs with missing scale evidence;
  - eligible financial docs with suspicious scale evidence;
  - eligible financial docs with classifier evidence missing;
  - candidate-selection errors;
  - document-family policy gaps.
- Identify the top one to three repeated root causes.
- Decide whether `scale_unknown` failures share one fix or are heterogeneous.
- Decide whether `classifier_low_confidence` failures are valid abstentions or
  missing deterministic evidence.
- Do not implement broad fixes unless a narrow source-bound tested root cause is
  proven.

## Safe Extension Allowance

Allowed only if proven by this audit:

- Source-bound scale evidence propagation.
- Narrow document-family classifier evidence rules.
- Candidate exclusion for obvious non-financial docs.
- Report-only diagnostics.
- Tests for each fixed class.

Do not infer scale broadly. Do not relax truth gates.

## Hard Stops

- No count-16/count-24 rerun.
- No broad extraction or backfill.
- No DB, Qdrant, news, or memory mutation.
- No source PDF edits.
- No prompt, gold-label, schema, runtime, model, or GPU config changes.
- No service restarts.
- No broad gate loosening.
- No unrelated cleanup.

## Validation

- Focused pytest if code/tests are touched.
- `py_compile` and ruff if code is touched and available.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- No source PDFs staged.
- Registry `list-active`.
- Explicit no sample/backfill rerun statement.

## Final Report

Report the failure table for all thirteen failed docs, root-cause buckets, fixes
made if any, next targeted repair task, whether another bounded sample is
justified, and remaining `DATA_MISSING`.
