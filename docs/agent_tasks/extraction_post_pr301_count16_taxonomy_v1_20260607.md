---
job_id: extraction_post_pr301_count16_taxonomy_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr301_count16_taxonomy_v1_20260607.md
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/failure_taxonomy.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/accepted_output_audit.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/source_text_audit.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR301 Count-16 Failure And Accepted-Output Taxonomy

## Objective

Classify every failed, low-confidence, and suspicious accepted document from
the post-PR301 count-16 sample. Decide whether one narrow follow-up repair is
justified and whether a count-24 approval packet is reasonable or premature.

## Scope

Branch:
`safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`.

Worktree:
`/home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607`.

Mode: AUDIT FIRST / SAFE EXTENSION / NO ADDITIONAL SAMPLE.

Risk: HIGH.

## Input Evidence

- Milestone 3 task card:
  `docs/agent_tasks/extraction_post_pr301_count16_validation_v1_20260607.md`.
- Milestone 3 report:
  `reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/`.
- Required PR #301 merge commit:
  `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`.

## Contract Check

Target system layer: extraction source classification, period/scale gates,
accepted-output quarantine behavior, and evaluation taxonomy.

Relevant contract rules: canonical financial values must be explicit,
source-bound, deterministic, auditable, and provenance-linked. Backend
extraction remains authoritative. No broad inference, prompt change, schema
change, gold-label change, or storage mutation is allowed.

What must not change: source PDFs, prompts, gold labels, canonical metric
ontology, schemas, runtime/model/GPU/service configuration, DB/Qdrant/news/
memory stores, broad ticker-universe execution, count-24, count-32, or broad
backfill.

Why safe: the phase starts report-local from the already bounded count-16
artifacts and permits code changes only for one clearly supported,
source-bound, focused repair with tests.

GPU process check required: no. This phase does not start a new extraction
sample.

## Required Audit

- List each doc, ticker, title, source path, document class, final status, gate,
  and side effects.
- Bucket every failed, low-confidence, or suspicious accepted document as one
  of:
  - true noncandidate;
  - eligible doc missing scale evidence;
  - eligible doc suspicious scale;
  - classifier evidence missing;
  - period/source mismatch;
  - insufficient metrics;
  - parser/table coverage gap;
  - accepted-output risk;
  - side-effect anomaly;
  - DATA_MISSING.
- Identify the top repeated root cause.
- Decide whether another narrow fix is justified.
- Decide whether count-24 approval is reasonable or premature.

## Narrow Repair Rules

Implement at most one narrow repair only if the audit shows one clear,
source-bound, testable root cause. Allowed repair classes include:

- one additional candidate exclusion class;
- one source-bound scale marker propagation fix;
- one stricter accepted-output quarantine or abstain guard;
- one row-label guard preventing a misleading label from mapping to a canonical
  metric;
- one report-only diagnostic if a code fix is not safe.

Forbidden repair classes: broad scale inference, loosening validation gates,
canonical metric expansion without explicit contract decision, disclosure rows
as canonical metrics, or multi-class broad refactor.

## Hard Stops

- No broad extraction/backfill.
- No full ticker-universe extraction.
- No count-24 or count-32.
- No additional count-16 sample.
- No direct SQL mutation.
- No Qdrant/news/memory mutation.
- No source PDF edits.
- No prompt, gold-label, runtime, model, GPU, or schema changes.
- No dirty parent-batch merge, rebase, reset, stash, delete, or unrelated
  cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr301_count16_taxonomy_v1_20260607.md`
- Safe registry active-record inspection or `DATA_MISSING`.
- JSON validation for generated report artifacts.
- Focused pytest if code changed.
- `python3 -m py_compile` for touched Python files if code changed.
- Ruff on touched Python files if available and code changed.
- `git diff --check`.
- `git diff --cached --check` if staging.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr301_count16_taxonomy_v1_20260607.md --repo-root .`
- Verify no source PDFs are staged.

## Final Report Requirements

Report the failure taxonomy, low-confidence taxonomy, suspicious accepted-output
audit, source evidence inspected, repair decision, validation status, files
touched, unsafe actions avoided, `DATA_MISSING`, and the final recommended
decision. Explicitly state that no additional sample, broad extraction,
backfill, count-24/count-32, or full ticker extraction ran in this phase.
