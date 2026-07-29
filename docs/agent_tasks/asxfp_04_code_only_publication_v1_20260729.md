---
job_id: asxfp_04_code_only_publication_v1_20260729
title: Publish ASXFP Ticket 04 extraction contracts without protected corpus artifacts
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "The owner approved the code-only publication lane by replying proceed."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_04_code_only_publication_v1_20260729
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/asxfp_04_code_only_publication_v1_20260729.md
  - docs/extraction/asx_document_extraction_contracts.md
  - financial-engine_v2/backend/app/services/asx_document_type_classifier.py
  - financial-engine_v2/backend/app/services/asx_document_type_sidecar.py
  - financial-engine_v2/backend/app/services/asx_extraction_contracts.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/manifest.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/quarterly_report_basic.json
  - financial-engine_v2/backend/tests/test_asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py
  - financial-engine_v2/backend/tests/test_asx_extraction_contracts.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/extraction/metric_extraction_contract.md
  - docs/extraction/asx_document_extraction_contracts.md
docs_changed:
  - docs/agent_tasks/asxfp_04_code_only_publication_v1_20260729.md
  - docs/extraction/asx_document_extraction_contracts.md
docs_followup: NONE
reason: "Ticket 04 introduces a durable document-type contract and fail-closed extraction boundary."
task_tier: standard
---

# ASXFP Ticket 04 code-only publication

## Objective

Port the reviewed Ticket 04 implementation from local commit
`03cf21dfd44a89132853be5cc03f40aa8000448a` onto live public canonical
`fa31262337be4329533d36951ca8e290b2606b98`, validate it, push only the
allowlisted code/docs/tests, and open a draft pull request.

## Custody boundary

- Keep `financial-engine_v2/data/asx_release_corpus/v1` and all protected
  source, label, manifest, hash, partition, and review artifacts local.
- Exclude Codex X launch records, worker reports, local validation reports,
  rollout paths, and local-machine metadata.
- Synthetic classifier fixtures are publishable code-test inputs and contain
  no protected corpus material.

## Forbidden actions

- No extraction, OCR, product model/prompt, evaluation, backfill, or canary.
- No runtime, service, database, queue, Qdrant, GPU, production-data,
  migration, activation, or deployment action.
- No protected artifact read, mutation, staging, push, or publication.
- No merge, issue closure, branch deletion, or ready-for-review transition.
- No file outside `allowed_files`.

## Required validation

- Verify the starting branch, HEAD, upstream, remote, and clean status.
- Verify existing changed paths match the reviewed implementation base.
- Run changed-file Ruff lint, focused Ticket 02-04 tests, Python compilation,
  JSON parsing, and `git diff --check`.
- Verify the changed path set equals this allowlist.
- Verify the protected corpus path has no diff and is absent from the commit.
- Commit, push with upstream tracking, and open a draft PR against
  `migration/clean-runtime-baseline-reconstruct-v1`.
