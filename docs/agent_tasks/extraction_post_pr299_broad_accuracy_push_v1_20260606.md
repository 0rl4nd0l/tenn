---
job_id: extraction_post_pr299_broad_accuracy_push_v1_20260606
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr299_broad_accuracy_push_v1_20260606.md
  - docs/agent_tasks/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606.md
  - docs/agent_tasks/extraction_post_pr299_count16_validation_v1_20260606.md
  - docs/agent_tasks/extraction_post_pr299_count16_failure_taxonomy_v1_20260606.md
  - reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/README.md
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/source_classification_audit.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/status.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/validation.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/diff-check.json
  - reports/agent_jobs/extraction_post_pr299_candidate_exclusion_taxonomy_v1_20260606/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_post_pr299_broad_accuracy_push_v1_20260606
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_96_comment_only_after_meaningful_milestone
---

# Post-PR299 Broad Accuracy Push

## Objective

Push Tenn extraction closer to broad accuracy after PR #299 by completing the
next safe sequence: candidate-exclusion taxonomy repair, one bounded count-16
validation sample, and at most one narrow follow-up repair if evidence supports
it.

## Scope

Lane: Financial Truth.

Supporting lanes: Evaluation, Query Orchestration, Provenance.

Branch:
`safe/extraction-post-pr299-broad-accuracy-push-v1-20260606`.

Worktree:
`/home/l4nd0/tenn-post-pr299-broad-accuracy-push-v1-20260606`.

Execution mode: LONG-RUNNING SAFE PROGRESS / AUDIT FIRST / SAFE EXTENSION /
BOUNDED VALIDATION.

## Contract Check

Target system layer: Extraction and Evaluation. Phase 1 touches deterministic
source-document classification before extraction execution; Phase 2 is
report-local bounded validation; Phase 3 may touch one narrow extraction or
evaluation guard only if source-bound evidence supports it.

Relevant contract rules: backend remains the sole authority; metric extraction
must extract explicit source values only; no inference or substitution; no
storage, retrieval, schema, prompt, model, or vector mutation; no broad backfill.

What must not change: source PDFs, gold labels, prompts, canonical metric
ontology, runtime/model/GPU/service config, DB/Qdrant/news/memory stores,
schemas, broad ticker-universe execution, or production persistence behavior.

Why safe: the work starts with deterministic noncandidate classification for
known false-positive document classes, validates focused tests before any
sample, then limits runtime validation to exactly one bounded count-16 sample.

GPU process check required: yes before Phase 2 only. Phase 1 does not start or
depend on llama-server.

## Hard Stops

- Do not run broad backfill, full ticker-universe extraction, count-24, or
  count-32.
- Do not mutate production DBs, Qdrant, Redis, news stores, Tenn memory, source
  PDFs, gold labels, extraction prompts, schemas, runtime configuration, model
  routing, or service state beyond the minimal bounded validation route.
- Do not implement broad fuzzy exclusions or inference-based financial truth.
- Do not merge dirty NVMe parent-batch work.
- Stop if Phase 1 validation fails or cannot be committed cleanly.
- Stop after one count-16 sample; do not run additional samples automatically.

## Phases

1. Candidate-exclusion taxonomy repair for known false-positive source classes.
2. One bounded count-16 validation sample if Phase 1 validates and commits.
3. Failure taxonomy and one narrow repair only if Phase 2 evidence supports it.
4. Stop with one final decision:
   `READY_FOR_COUNT24_APPROVAL_PACKET`, `NEEDS_ANOTHER_TARGETED_FIX`,
   `NEEDS_ACCEPTED_OUTPUT_AUDIT`, `BLOCKED_BY_RUNTIME`, `BLOCKED_BY_POLICY`,
   `BLOCKED_BY_PARKED_WORK`, or `BLOCKED_BY_REPO_HYGIENE`.

## Validation

- Current-turn repo preflight: path, branch, HEAD, remote, status, worktrees,
  and PR #299 ancestry.
- Safe registry evidence or `DATA_MISSING` if `list-active` is not safely
  available.
- Validate each task card before edits.
- Phase-specific focused pytest, py_compile, ruff if available, JSON
  validation, `git diff --check`, task-card `check-diff`, and source-PDF staging
  audit.

## Final Report Requirements

Report phases completed/skipped, commits created, validation results, count-16
result if run, failure and low-confidence taxonomy, unsafe-row/side-effect
audit, exact next recommended task, `DATA_MISSING`, and explicit confirmation
that no broad extraction, backfill, or full ticker extraction ran.
