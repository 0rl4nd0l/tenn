---
job_id: asxfp_ticket04_half_year_bundle_followup_v1_20260729
title: Repair cross-page half-year bundle precedence for ASXFP Ticket 04
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "The owner started a /goal to use Codex X to complete the remaining tickets and said Go."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_ticket04_half_year_bundle_followup_v1_20260729
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/asxfp_ticket04_half_year_bundle_followup_v1_20260729.md
  - docs/extraction/asx_document_extraction_contracts.md
  - financial-engine_v2/backend/app/services/asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_document_type_classifier.py
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket04_half_year_bundle_followup_v1_20260729/README.md
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/extraction/asx_document_extraction_contracts.md
docs_changed:
  - docs/agent_tasks/asxfp_ticket04_half_year_bundle_followup_v1_20260729.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket04_half_year_bundle_followup_v1_20260729/README.md
docs_followup: "Update the extraction-contract documentation only if the public classifier behavior needs clarification."
reason: "A local diagnostic exposed a new cross-page half-year bundle failure class after the first Ticket 04 repair merged."
task_tier: standard
---

# ASXFP Ticket 04 half-year bundle follow-up

## Objective

From canonical commit `b01885d6cd55242339662e91d18141aeb725f089`
plus the authorized orchestration-only seed commits, make deterministic
whole-document half-year precedence recognize a substantive half-year report
whose required anchors are distributed across later pages after an Appendix 4D
wrapper.

## Worker identity

- The canonical product base is
  `b01885d6cd55242339662e91d18141aeb725f089`.
- The worker's expected `HEAD` is the exact remote-pinned seed SHA supplied by
  the launcher as `CODEX_X_SOURCE_SHA`; it is intentionally later than the
  canonical product base because it contains only this task card and goal
  reports.
- Verify `HEAD == CODEX_X_SOURCE_SHA`, verify the canonical product base is an
  ancestor, and verify the committed
  `b01885d6cd55242339662e91d18141aeb725f089..HEAD` path set is limited to this
  task card and the two allowlisted report directories.
- Use the real Git binary with the launcher-provided `GIT_DIR` and
  `GIT_WORK_TREE` only for read-only identity commands if the bound Git wrapper
  cannot append its audit log under the offline permission profile. Do not
  bypass the bound wrapper for mutation, staging, commits, or remote access.

## Regression Adjudication

- target_identity: VERIFIED
- alleged_old_fix: VERIFIED
- canonical_lineage: VERIFIED
- current_repro: VERIFIED from the approved local diagnostic summary only
- scope_comparison: broader
- permanent_gate: missing
- runtime_functionality_proof: not_required
- classification: NEW_FAILURE_CLASS
- next_action: add the cross-page synthetic regression, then implement the
  narrow classifier repair

The merged Ticket 04 repair correctly handles a complete later report page.
The newly observed failure distributes `Half-Year Report` and
`Interim financial report` evidence across separate later pages, so no single
page reaches the current high-confidence threshold. This is a new failure
class, not proof that the merged fix regressed.

## Required behavior

- Add a synthetic RED regression with an Appendix 4D wrapper on an early page,
  `Half-Year Report` on one later page, and substantive interim-report evidence
  on another later page.
- Aggregate only source-bound half-year evidence from pages later than the
  Appendix 4D wrapper.
- Require the normal high-confidence half-year anchor contract across that
  later-page evidence before selecting `half_year_report`.
- Preserve fail-closed behavior for same-page wrapper/report ambiguity,
  weak bundles, ordinary Appendix 4D documents, and high-confidence annual or
  quarterly conflicts.
- Keep classification metadata-only: it must not prove a metric or authorize
  extraction, persistence, or canonical writes.

## Hard stops

- Do not access any source PDF, protected label, diagnostic or holdout corpus
  path, release manifest, local diagnostic artifact, or protected metadata.
- Do not run extraction, OCR, a model or prompt, evaluation, backfill, canary,
  runtime, service, database, queue, Qdrant, GPU, deployment, activation, or
  production-data action.
- Do not edit outside `allowed_files`.
- Do not merge, deploy, activate, close issues, or mark the PR ready.
- Do not broaden this ticket to the separate anchor-absent 172-page document;
  that case remains `DATA_MISSING` pending an authorized source-bound metadata
  seam or new deterministic evidence.

## Worker protocol

- Use one fresh Codex X implementer session.
- Validate this task card before product edits.
- Work test-first: demonstrate the new focused test failing before the minimal
  implementation and passing after it.
- Freeze the exact delta after implementation.
- Use a different fresh Codex X session for independent read-only review.
- The parent Codex owns acceptance, commit, push, and draft-PR publication.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket04_half_year_bundle_followup_v1_20260729.md`
- Focused RED/GREEN pytest for the new cross-page regression.
- Full `financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`.
- Existing Ticket 04 focused classifier/contract/multipass tests where
  available.
- Ruff for changed Python.
- `python3 -m py_compile` for changed Python.
- `git diff --check`.
- Task-card `check-diff`.
- Confirm no source PDF, binary, protected corpus artifact, or local diagnostic
  output is staged.

## Closeout

Return exact base, branch, candidate tree, changed files, RED and GREEN
commands, validation status, reviewer verdict, remaining risks, and docs impact.
Publication may create a draft PR only; merge remains a separate approval.
