---
job_id: asxfp_03_release_holdout_contract_repair_v1_20260728
title: Repair Ticket 03 per-class diagnostic and holdout partition validation
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/asxfp_03_release_holdout_contract_repair_v1_20260728
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allowed_files:
  - docs/agent_tasks/asxfp_03_release_holdout_contract_repair_v1_20260728.md
  - financial-engine_v2/backend/app/services/asx_holdout_confidentiality.py
  - financial-engine_v2/backend/app/services/asx_release_corpus.py
  - financial-engine_v2/backend/tests/test_asx_holdout_confidentiality.py
  - financial-engine_v2/backend/tests/test_asx_release_corpus.py
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - /home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/docs/plans/asx_financial_profile_extraction_recovery_plan.md
  - /home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/docs/superpowers/specs/2026-07-23-asx-financial-profile-extraction-recovery.md
docs_changed:
  - docs/agent_tasks/asxfp_03_release_holdout_contract_repair_v1_20260728.md
docs_followup: NONE
reason: "The release-corpus validator must document and enforce the governing two-diagnostic and six-holdout documents per Ticket 02 class."
task_tier: medium
recommended_model: "Codex standard coding model"
actual_model: "Codex GPT-5.6"
why_this_model: "The repair is a narrow financial-truth invariant with a source-bound counterexample and exact public validator interface."
worker_model_allowed: false
worker_decision_limit: "No delegated implementation or decision authority."
escalation_needed: false
---

# ASXFP Ticket 03 Release Holdout Contract Repair

## Objective

Require each of the six Ticket 02 document classes to contain exactly two
diagnostic documents and six release-holdout documents.

## Source-bound requirement

- The governing plan selects eight documents per class.
- It designates two documents from every class for the 12-document diagnostic
  set.
- The remaining six documents per class form the 36-document release holdout.

## Allowed work

- Normalize PR #526 onto the current canonical ancestry without changing its
  reviewed product tree.
- Add one fail-closed per-class partition invariant to
  `validate_release_corpus`.
- Add one regression that preserves global 12/36 counts while skewing the
  per-class distribution.
- Retain the two unchanged holdout-confidentiality files inherited from the
  original PR #526 head; they are allowlisted only because validation compares
  the cumulative PR diff against canonical.
- Update existing draft PR #526 and carry its repaired base into draft PR #527.

## Forbidden work

- No source PDF, gold-label, manifest, protected review-record, or
  production-data access or mutation.
- No extraction, OCR/model, prompt/model configuration, service, runtime,
  database, queue, Qdrant, GPU, backfill, activation, deployment, or PR merge.
- No ontology, metric-definition, score-threshold, or broad corpus redesign.
- No file outside `allowed_files`.

## Required validation

- Task-card validation and allowlist diff check.
- RED counterexample proving the current validator accepts a skewed per-class
  split.
- GREEN focused release-corpus tests.
- Changed-file Ruff and format checks.
- `git diff --check`.
- Fresh exact-head CI on PR #526.

## Done criteria

- Global 12/36 counts cannot mask an invalid per-class partition.
- Every class requires exactly two diagnostic and six holdout documents.
- Existing valid release-corpus behavior remains green.
- PR #526 is based on current canonical ancestry and has fresh terminal CI.
