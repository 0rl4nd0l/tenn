---
job_id: asxfp_ticket05_observation_seam_v1_20260729
title: Introduce the immutable financial-observation seam for ASXFP Ticket 05
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
output_dir: reports/agent_jobs/asxfp_ticket05_observation_seam_v1_20260729
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/asxfp_ticket05_observation_seam_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - financial-engine_v2/backend/app/alembic/versions/0010_financial_observations.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/models/__init__.py
  - financial-engine_v2/backend/app/models/financial_observations.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket05_observation_seam_v1_20260729/README.md
docs_impact: DOCS_REQUIRED
docs_checked:
  - docs/extraction
docs_changed:
  - docs/agent_tasks/asxfp_ticket05_observation_seam_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket05_observation_seam_v1_20260729/README.md
docs_followup: "Document the immutable identity, trust, atomicity, idempotence, and compatibility-read contracts."
reason: "The hash-pinned ASXFP programme declares Ticket 05 ready and no equivalent immutable observation seam exists in canonical."
task_tier: standard
---

# ASXFP Ticket 05 immutable observation seam

## Authority

- Canonical product base:
  `b01885d6cd55242339662e91d18141aeb725f089`.
- Authoritative ticket:
  `.scratch/asx-financial-profile-extraction-recovery/issues/05-immutable-observation-seam.md`
  at SHA-256
  `27f03834bba372c3c3f470cf1a1fa7f90b7a586b7015e6b453a77599920aac78`.
- Authoritative specification SHA-256:
  `ecba77e0185fe5fe4d38c840624bb7da4ce5f4f6290458c7f6e2b33b3a8b8b67`.
- Authoritative plan SHA-256:
  `16ff026fa5cec820f9ce4cbe558b6fb4d168e6fc0e23c98854d81b1abf4b12ba`.
- Ticket 05 is declared `ready-for-agent` and `Blocked by: None`.

## Worker identity

- The worker's expected `HEAD` is the exact remote-pinned seed SHA supplied by
  the launcher as `CODEX_X_SOURCE_SHA`. It is later than the canonical product
  base only by this task card and report-local orchestration evidence.
- Verify `HEAD == CODEX_X_SOURCE_SHA`, verify the canonical product base is an
  ancestor, and verify the committed
  `b01885d6cd55242339662e91d18141aeb725f089..HEAD` path set is limited to this
  task card and the two allowlisted report directories.
- Use the real Git binary with launcher-provided `GIT_DIR` and `GIT_WORK_TREE`
  only for read-only identity commands if the bound wrapper cannot append its
  audit log under the offline permission profile. Do not bypass the bound
  wrapper for mutation, staging, commits, or remote access.

## Objective

Carry the existing statutory `revenue` metric from the production
single-document workflow through an immutable observation persistence seam and
into a deterministic company-financial read, while retaining the existing
`asx_periodic_financials` write and response shape as a compatibility
projection.

## Required behavior

- Add an immutable financial-observation model and Alembic migration.
- Every accepted observation identifies:
  - source document and extraction run/version;
  - ticker, metric, numeric value, period end and period basis;
  - accounting basis, native currency and absolute-unit scale;
  - source-bound field provenance; and
  - explicit trust state.
- The immutable identity must permit different documents, extraction versions,
  period bases, and accounting bases for the same ticker/period/metric.
- Reprocessing the same source document and extractor version with the same
  financial context is idempotent. A retry must not mutate the accepted row.
- Missing or ambiguous metric value, period, period basis, accounting basis,
  currency, scale, provenance, or accepted trust state must abstain from
  observation persistence. Do not invent defaults from document type.
- Stage the observation and `ExtractionRun` in the same SQLAlchemy transaction;
  the seam must not call `commit()`. The existing workflow remains the sole
  transaction owner and retains one commit for the extraction run,
  observation, and legacy compatibility row.
- Add a small deterministic read interface used by the existing
  `/financials` route. For the one promoted metric, return accepted statutory
  observation truth without changing the existing response shape or removing
  the legacy row fallback.
- If accepted statutory observations conflict at the same read identity,
  abstain from overriding the legacy compatibility value. Do not resolve by
  insertion time or write order.
- Keep the implementation narrow to `revenue`. Tickets 06–10 own broader
  statutory projection, period-basis expansion, accounting-basis separation,
  and restatement precedence.

## Hard stops

- Do not access any source PDF, protected label, diagnostic/holdout corpus,
  release manifest, local diagnostic output, or protected metadata.
- Do not run extraction, OCR, a model or prompt, evaluation, runtime, service,
  database or migration execution, queue, Qdrant, GPU, deployment, activation,
  canary, backfill, or production-data action.
- Tests must use pure fakes/mocks and must not create or connect to a database.
- Do not edit outside `allowed_files`.
- Do not merge, deploy, activate, close issues, or mark a PR ready.
- Do not add adjusted results, derive metrics, perform FX conversion, select
  restatements, or retire legacy direct writes.

## Worker protocol

- Use one fresh Codex X implementer session.
- Validate this task card before product edits.
- Work test-first and record focused RED/GREEN evidence without a database.
- Freeze the exact delta after implementation.
- Use a different fresh Codex X session for independent read-only review.
- The parent Codex owns acceptance, commit, push, and draft-PR publication.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket05_observation_seam_v1_20260729.md`
- Focused RED/GREEN tests in
  `financial-engine_v2/backend/tests/test_financial_observations.py`.
- Existing focused pipeline/API/model import tests that do not connect to a
  database.
- Alembic migration import/structure inspection only; do not run migrations.
- Ruff for changed Python.
- `python3 -m py_compile` for changed Python.
- `git diff --check`.
- Task-card `check-diff`.
- Confirm no PDF, binary, protected corpus artifact, or runtime output is
  staged.

## Closeout

Return exact base, branch, candidate tree, changed files, RED and GREEN
commands, validation status, reviewer verdict, remaining risks, and docs
impact. Publication may create a draft PR only; merge and any database-backed
proof remain separate approvals.

## CI repair evidence

- Repair base: `ef74875be105bd2dbe6feb101044d3dd1069e363`, tree
  `0997bbbe88ce8a49dd3c55f72eb3060d3a5d0374`.
- GitHub Actions run `30458351620` exposed one failure:
  `test_no_random_uuid_generation_in_pipeline` rejected random canonical
  observation identity generation.
- The repair maps the complete
  `uq_financial_observation_source_context` identity to a deterministic,
  versioned UUIDv5. Retry run identity is excluded, matching the database
  uniqueness contract.
- Focused fake-only coverage proves retry stability and differentiation when
  each currently variable identity dimension changes. No invariant relaxation,
  database, migration, runtime, protected-data, or remote action is used.
