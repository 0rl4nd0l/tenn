---
job_id: extraction_post_pr301_broad_accuracy_push_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr301_broad_accuracy_push_v1_20260607.md
  - docs/agent_tasks/extraction_post_pr301_dxc_lbl_containment_v1_20260607.md
  - docs/agent_tasks/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607.md
  - docs/agent_tasks/extraction_post_pr301_count16_validation_v1_20260607.md
  - docs/agent_tasks/extraction_post_pr301_count16_taxonomy_v1_20260607.md
  - reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/raw_commands.log
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/pre_containment_snapshot.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/post_containment_verification.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/containment_ledger.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/raw_commands.log
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/source_classification_audit.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_candidate_exclusion_taxonomy_v1_20260607/raw_commands.log
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
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_96_comment_only_after_meaningful_milestone
---

# Post-PR301 Broad Accuracy Push

## Objective

Push Tenn extraction closer to broad, accurate, evidence-bound financial metric
extraction after PR #301 by completing the next safe sequence:

1. DXC/LBL exact accepted-output containment.
2. Candidate-exclusion taxonomy hardening.
3. Exactly one bounded count-16 validation sample.
4. Failure and accepted-output taxonomy.
5. At most one narrow follow-up repair if the evidence clearly supports it.

## Scope

Branch:
`safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`.

Worktree:
`/home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607`.

Execution mode: LONG-RUNNING SAFE PROGRESS / CONTROLLED CONTAINMENT / SAFE
EXTENSION / BOUNDED VALIDATION.

Risk: HIGH for financial truth.

## Contract Check

Target system layer: extraction accepted-output containment, deterministic
source-document classification, bounded evaluation, and source-bound metric
truth gates.

Relevant contract rules: canonical financial values must be explicit,
source-bound, deterministic, auditable, and provenance-linked. Backend
extraction remains authoritative. Do not infer values, broaden ontology, promote
disclosure rows silently, or relax validation gates.

What must not change: source PDFs, prompts, gold labels, canonical metric
ontology, schemas, runtime/model/GPU/service configuration, broad ticker
execution, count-24/count-32, broad backfill, or full ticker-universe
extraction.

Why safe: the work starts by containing only exact DXC/LBL accepted-output risk
identified by PR #301 evidence, then hardens known deterministic candidate
classes, runs exactly one count-16 validation, and stops before broader
sampling or backfill.

GPU process check required: yes before the bounded count-16 validation phase
only. Report-only and source-classification phases do not depend on
llama-server.

## Hard Stops

- Stop if current HEAD does not include PR #301 merge commit
  `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`.
- Stop on active overlapping registry/runtime jobs.
- Stop before broad backfill, full ticker-universe extraction, count-24, or
  count-32.
- Stop before production mutation outside exact approved DXC/LBL containment.
- Stop before DB/Qdrant mutation unless exact DXC/LBL rows or points are
  identified and pre-snapshotted.
- Stop before source PDF edits, prompt/gold-label/schema/runtime/model/GPU
  config changes, dirty parent-batch merge, unrelated cleanup, stash, reset,
  rebase, branch deletion, or merge.
- Stop if unsafe accepted outputs appear and cannot be contained or
  quarantined.

## Milestones

1. DXC/LBL exact accepted-output containment or no-op proof.
2. Candidate-exclusion taxonomy hardening.
3. Exactly one bounded count-16 validation sample.
4. Failure and accepted-output taxonomy.
5. At most one narrow follow-up repair if the taxonomy shows one clear,
   source-bound, testable root cause.
6. Stop with one final decision:
   `READY_FOR_COUNT24_APPROVAL_PACKET`,
   `NEEDS_ANOTHER_TARGETED_FIX`,
   `NEEDS_ACCEPTED_OUTPUT_CONTAINMENT`,
   `NEEDS_RUNTIME_OBSERVABILITY_FIX`,
   `NEEDS_PARKED_WORK_REVIEW`,
   `BLOCKED_BY_POLICY`, or
   `BLOCKED_BY_DATA_MISSING`.

## Validation

- Current-turn repo preflight: path, branch, HEAD, remote, origin fetch, status,
  worktrees, and PR #301 ancestry.
- Safe registry evidence by direct read-only active-record inspection, or
  `DATA_MISSING` if only lock-writing CLI evidence exists.
- Validate each task card before edits.
- Phase-specific focused pytest, py_compile, ruff if available, JSON
  validation, `git diff --check`, `git diff --cached --check` if staging,
  task-card `check-diff`, and source-PDF staging audit.

## Final Report Requirements

Report canonical starting HEAD and final HEAD, phases completed or skipped,
commits created, DXC/LBL containment result, candidate-exclusion rules added,
count-16 result if run, failure and accepted-output taxonomy, any Milestone 5
repair, side-effect audit, count-24 approval decision, remaining
`DATA_MISSING`, exact next recommended prompt, Project Memory save
recommendation, and explicit confirmation that no broad extraction, backfill,
or full ticker extraction ran.
