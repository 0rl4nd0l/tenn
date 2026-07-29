---
job_id: asxfp_ticket04_real_diagnostic_classifier_repair_v1_20260729
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/asxfp_ticket04_real_diagnostic_classifier_repair_v1_20260729.md
  - docs/extraction/asx_document_extraction_contracts.md
  - financial-engine_v2/backend/app/services/asx_document_type_classifier.py
  - financial-engine_v2/backend/app/services/asx_extraction_contracts.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_extraction_contracts.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
output_dir: reports/agent_jobs/asxfp_ticket04_real_diagnostic_classifier_repair_v1_20260729
---

# ASXFP Ticket 04 Real-Diagnostic Classifier Repair

## Objective

Repair deterministic ASX document-type classification from exact canonical base
`424b699f8920a803e992433d9a95c775f60efd87` using only synthetic text inputs.
Collect page-aware evidence, apply fail-closed whole-document bundle precedence,
and preserve metadata-only contract selection.

## Local Diagnostic Evidence

The user supplied these immutable provenance identifiers and summarized failure
classes. They may guide synthetic regression cases but the artifacts and any
paths or corpora they reference must not be accessed:

- `classifier_diagnostic.json`:
  `2e1e9fcb3885d9bdf706b668c7699f1a90feb0b7cbfdffed5bac430f8fd918c0`
  (6/12 correct);
- `pdf_metadata_title_sensitivity.json`:
  `026d7b7631994a103f6481fa1cb460994eb49852fafda2fa13bf88ec274007a4`
  (7/12 correct);
- `failed_document_anchor_locations.json`:
  `d2efe1592e3b97bd6729125d58bb33b0a747d0372d0e3ce390ee49c78ed2ddac`.

Failure classes to encode synthetically are an Appendix 4C beginning on page 2
behind a generic quarterly cover, Appendix 5B beginning on page 9 or 11 behind
quarterly-activities covers, half-year bundles containing Appendix 4D followed
by later half-year-report evidence, and an image-heavy annual cover rescued by
title metadata.

## Required Behavior

- Accept deterministic page-numbered text evidence from parsed document
  sections without reading source files.
- Find supported Appendix 4C/5B anchors beyond page 1 despite a generic
  quarterly cover.
- Give a later, substantive half-year report whole-document precedence over an
  Appendix 4D wrapper in the same bundle.
- Use supplied announcement/PDF title metadata to classify an otherwise
  low-text annual-report cover.
- Fail closed on unsupported or genuinely conflicting bundles.
- Preserve first-page conflicting-anchor abstention.
- Keep classification and extraction-contract selection metadata-only:
  `canonical_write`, metric-evidence, and persistence authority remain false.
- Do not widen canonical metrics, aliases, parser authority, or write authority.

## Test Seams and TDD

The agreed public seams are `classify_asx_document_type()`,
`classify_and_select_extraction_contract()`, and
`run_multipass_extraction()`. Add synthetic text-only regressions one vertical
slice at a time, demonstrate RED before each minimal GREEN implementation, and
do not use source documents or diagnostic fixtures.

## Hard Stops

- Do not access any source PDF, gold label, diagnostic or holdout corpus path,
  release manifest, database, service, queue, GPU, model, OCR, metric
  extraction, runtime, deployment, activation, or production data.
- Do not run an extraction job or invoke a parser/model against a real file.
- Do not change metric ontology, canonical-write authority, persistence,
  deployment, runtime configuration, prompts, or production data.
- Do not edit outside `allowed_files`.
- Do not push, open a PR, merge, deploy, activate, or mutate external state.

## Validation

- Validate this task card before product edits.
- Focused synthetic Ticket 04 pytest tests (RED, then GREEN).
- Existing focused tests for the three allowed test modules.
- Ruff for changed Python.
- `python3 -m py_compile` for changed Python.
- JSON validation if any JSON is changed (none planned).
- `git diff --check`.
- Task-card `check-diff`.
- Confirm no source PDF or binary is staged.
- Make one local commit only when all checks are green.

## Final Report

Return exact branch, base SHA, commit SHA, changed files, tests and exit status,
remaining risks, and docs-impact fields. Confirm prohibited runtime/data actions
did not occur and no remote mutation was attempted.
