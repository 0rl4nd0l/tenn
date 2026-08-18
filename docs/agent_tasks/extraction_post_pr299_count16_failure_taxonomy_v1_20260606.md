---
job_id: extraction_post_pr299_count16_failure_taxonomy_v1_20260606
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr299_count16_failure_taxonomy_v1_20260606.md
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/failure_taxonomy.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/accepted_output_audit.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/source_text_audit.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_pr299_count16_failure_taxonomy_v1_20260606
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR299 Count-16 Failure Taxonomy

## Objective

Audit every failed or suspicious count-16 output from the post-PR299 bounded
validation sample, identify the next narrow root cause, and implement at most
one narrow source-bound repair only if the evidence is clear and testable.

## Scope

Branch:
`safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`.

Worktree:
`/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606`.

Mode: AUDIT FIRST / SAFE EXTENSION / BOUNDED VALIDATION. Do not run another
sample in this phase.

Risk: MEDIUM/HIGH.

## Input Evidence

- Phase 2 task card:
  `docs/agent_tasks/extraction_post_pr299_count16_validation_v1_20260606.md`.
- Phase 2 report:
  `reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606/`.
- Required baseline merge commit:
  `9436d1d32de0da5423b8edcfc7efc883ccac3fd6`.
- Required Phase 1 repair commit:
  `9c9107bbbbac6a2971b57d9df5473aa870bb4b28`.
- Required Phase 2 validation commit:
  `12e6042910434fb09fec07999927209a7538bb70`.

## Contract Check

Target system layer: extraction source classification, period/scale gates,
accepted-output quarantine behavior, and evaluation taxonomy.

Relevant contract rules: canonical financial values must be explicit,
source-bound, deterministic, auditable, and provenance-linked; backend
extraction remains authoritative; no broad inference, prompt change, schema
change, gold-label change, or storage mutation is allowed.

What must not change: source PDFs, prompts, gold labels, canonical metric
ontology, schemas, runtime/model/GPU/service configuration, DB/Qdrant/news/
memory stores, broad ticker-universe execution, count-24, count-32, or
production persistence behavior.

Why safe: the phase starts report-local from the already bounded count-16
artifacts and permits code changes only for one clearly supported,
source-bound, focused repair with tests.

GPU process check required: no. This phase does not start a new extraction
sample or depend on llama-server.

## Required Audit

- List each failed or suspicious document with document ID, ticker, title,
  source path, document class, status, and gate.
- Bucket each finding as one of:
  - true noncandidate;
  - eligible doc missing scale evidence;
  - eligible doc suspicious scale;
  - classifier evidence missing;
  - period/source mismatch;
  - insufficient metrics;
  - parser/table coverage gap;
  - accepted-output risk.
- Audit suspicious accepted outputs from the same sample, especially known
  WHC/AZJ/DXC blockers and any newly evident accepted-output risk.
- Identify the top repeated root cause.

## Repair Rules

Implement at most one narrow repair only if the audit shows clear,
source-bound, testable evidence. Allowed repair classes include:

- an additional deterministic noncandidate exclusion for a repeated obvious
  false-positive class;
- source-bound scale marker propagation;
- a report-only diagnostic for WHC/AZJ/DXC-class behavior;
- stricter quarantine or abstain behavior for suspicious accepted rows.

Do not implement broad inference, broad fuzzy exclusions, relaxed truth gates,
or any repair that changes prompts, gold labels, schemas, source PDFs, or
runtime/model/service configuration.

## Hard Stops

- No broad extraction/backfill.
- No full ticker-universe extraction.
- No count-24 or count-32.
- No additional count-16 sample.
- No direct SQL mutation.
- No Qdrant/news/memory mutation.
- No source PDF edits.
- No prompt, gold-label, runtime, model, or schema changes.
- No dirty parent-batch merge, rebase, reset, stash, delete, or unrelated
  cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr299_count16_failure_taxonomy_v1_20260606.md`
- Safe registry/list-active evidence or `DATA_MISSING`.
- JSON validation for generated report artifacts.
- Focused pytest if code changed.
- `python3 -m py_compile` for touched Python files if code changed.
- Ruff on touched Python files if available and code changed.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr299_count16_failure_taxonomy_v1_20260606.md --repo-root .`
- Verify no source PDFs are staged.
- Commit if validation is clean.

## Final Report Requirements

Report the failure taxonomy, low-confidence taxonomy, suspicious accepted-output
audit, source evidence inspected, repair decision, validation status, files
touched, unsafe actions avoided, `DATA_MISSING`, and the recommended Phase 4
decision. Explicitly state that no additional sample, broad extraction,
backfill, count-24/count-32, or full ticker extraction ran.
