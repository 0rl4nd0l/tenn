---
job_id: asxfp_ticket07_quarter_ytd_v1_20260729
title: Preserve quarter-only and year-to-date observations for ASXFP Ticket 07
lane: Financial Truth
supporting_lanes:
  - Extraction
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "The owner started a /goal to use Codex X to complete the remaining ASXFP tickets."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_ticket07_quarter_ytd_v1_20260729
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/asxfp_ticket07_quarter_ytd_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - financial-engine_v2/backend/app/alembic/versions/0012_expand_observation_period_basis.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/models/financial_observations.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket07_quarter_ytd_v1_20260729/README.md
docs_impact: DOCS_REQUIRED
docs_checked:
  - docs/extraction
docs_changed:
  - docs/agent_tasks/asxfp_ticket07_quarter_ytd_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket07_quarter_ytd_v1_20260729/README.md
docs_followup: "Document explicit period-observation input, column-role binding, distinct identities, and additive profile reads."
reason: "Ticket 07 is ready after Tickets 04 and 05, and the stacked Ticket 06 head is independently accepted and exact-head green."
task_tier: standard
---

# ASXFP Ticket 07 quarter-only and year-to-date observations

## Authority

- Stacked product base:
  `f063c2a4cb4b9c677f35498de4b80f31dba55ba6`, the independently accepted and
  exact-head green Ticket 06 delivery head.
- Canonical ancestor:
  `b01885d6cd55242339662e91d18141aeb725f089`.
- Authoritative ticket:
  `.scratch/asx-financial-profile-extraction-recovery/issues/07-quarter-and-ytd-observations.md`
  at SHA-256
  `6c3630e469e58e5b7974bc687fa63ca3be8935d6a8b1a4cf049896098044d488`.
- Authoritative specification SHA-256:
  `ecba77e0185fe5fe4d38c840624bb7da4ce5f4f6290458c7f6e2b33b3a8b8b67`.
- Authoritative plan SHA-256:
  `16ff026fa5cec820f9ce4cbe558b6fb4d168e6fc0e23c98854d81b1abf4b12ba`.
- Ticket 07 is `ready-for-agent`; its Ticket 04 and Ticket 05 dependencies are
  satisfied in the current stacked ancestry.

## Worker identity

- The worker's expected `HEAD` is the exact remote-pinned seed SHA supplied by
  the launcher as `CODEX_X_SOURCE_SHA`. It is later than the stacked product
  base only by this task card and report-local goal evidence.
- Verify `HEAD == CODEX_X_SOURCE_SHA`, verify the stacked product base is an
  ancestor, and verify the committed
  `f063c2a4cb4b9c677f35498de4b80f31dba55ba6..HEAD` path set contains only this
  task card and the allowlisted report files.

## Objective

Extend the immutable observation seam so one quarterly announcement can
contribute both a current-quarter (`period_only`) view and a cumulative
(`year_to_date`) view without identity collision, legacy regression, or
evidence ambiguity.

## Required behavior

- Make `period_basis` first-class for new quarterly observations with the exact
  closed values `period_only` and `year_to_date`. Preserve the existing
  `Q`/`H`/`A` vocabulary for already-supported legacy observation contexts.
- Define and document one explicit multi-period structured-input collection.
  Each member must carry its own metrics, field provenance, period end,
  `period_basis`, source-period evidence, and source-period-end evidence.
  Retain the existing single-period input as a compatibility path.
- Bind `period_only` to an explicit current-quarter source column role and
  `year_to_date` to an explicit year-to-date source column role. Require the
  source cell to carry a non-negative column index, a non-empty header/raw
  value, and the matching closed role.
- Require basis-specific source-text evidence for both the period scope and the
  reporting-period end. Metadata-only, inferred, unknown, announcement-date,
  prior-period, and comparative evidence must abstain.
- A comparative, prior-period, date, or announcement-date column must never be
  relabelled as either accepted basis merely because it contains a numeric
  value or date.
- Stage every accepted metric independently for each accepted period member.
  One invalid member or metric must not suppress a valid sibling.
- Preserve deterministic UUIDv5 identity, PostgreSQL conflict-safe insertion,
  immutable provenance, caller-owned transaction behavior, and the ten-metric
  statutory/unit rules from Tickets 05–06. The two bases must produce distinct
  identities even when document, metric, and period end are otherwise equal.
- Add a forward-only stacked migration that expands only the closed
  `period_basis` check. Do not edit or execute published migrations. Keep ORM
  metadata exactly aligned with the migration.
- Return both bases through an additive company-profile read without collision.
  Preserve every existing `/financials` legacy row and field. New
  observation-only period rows or an equivalently additive representation must
  be deterministic, basis-labelled, sparse, conflict-abstaining, and must not
  overwrite a legacy `Q`/`H`/`A` row.
- Keep public Ticket 05–06 service compatibility aliases and legacy
  single-period behavior.

## Hard stops

- Do not access any source PDF, protected label, diagnostic/holdout corpus,
  release manifest, local diagnostic output, or protected metadata.
- Do not run extraction, OCR, a model or prompt, evaluation, runtime, service,
  database or migration execution, queue, Qdrant, GPU, deployment, activation,
  canary, backfill, or production-data action.
- Tests must use pure fakes/mocks and must not create or connect to a database.
- Do not edit outside `allowed_files`.
- Do not merge, deploy, activate, close issues, or mark a PR ready.
- Do not add Appendix 4C-specific extraction, adjusted accounting bases,
  restatement precedence, OCR, broad table selection, normalization policy, or
  legacy-write retirement. Tickets 08–15 own those changes.

## Worker protocol

- Use one fresh Codex X implementer session.
- Validate this task card before product edits.
- Work test-first and record focused RED/GREEN evidence without a database.
- Freeze the exact delta after implementation.
- Use a different fresh Codex X session for independent read-only review.
- The parent Codex owns acceptance, commit, push, and stacked draft-PR
  publication.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket07_quarter_ytd_v1_20260729.md`
- Focused RED/GREEN tests in
  `financial-engine_v2/backend/tests/test_financial_observations.py`.
- Static/fake coverage for two bases in one document, distinct IDs, invalid
  sibling isolation, source-column binding, comparative/date rejection,
  migration/ORM alignment, additive read behavior, and legacy compatibility.
- Existing focused observation and metric-contract tests that do not connect
  to a database.
- Alembic migration import/AST/structure inspection only; do not run
  migrations.
- Ruff and `python3 -m py_compile` for changed Python.
- `git diff --check` and task-card `check-diff`.
- Confirm no PDF, binary, protected corpus artifact, or runtime output is
  staged.

## Closeout

Return exact stacked base, branch, predecessor commit/tree, changed files,
RED/GREEN commands, validation status, reviewer verdict, remaining risks, and
docs impact. Publication may create a stacked draft PR against the Ticket 06
branch only; merge and database-backed proof remain separate approvals.

A tracked report records the latest frozen predecessor candidate commit/tree
and its pending report patch state. It must not embed the hash of its own
containing commit. The parent freeze and fresh independent reviewer or PR
record supply the final containing commit/tree.
