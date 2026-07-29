---
job_id: asxfp_ticket06_statutory_projection_v1_20260729
title: Project all ten statutory metrics through immutable observations for ASXFP Ticket 06
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
output_dir: reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/asxfp_ticket06_statutory_projection_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - financial-engine_v2/backend/app/alembic/versions/0011_expand_statutory_observation_metrics.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/services/financial_metric_contract.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729/README.md
docs_impact: DOCS_REQUIRED
docs_checked:
  - docs/extraction
docs_changed:
  - docs/agent_tasks/asxfp_ticket06_statutory_projection_v1_20260729.md
  - docs/extraction/financial_observation_contract.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/FRAME.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/OPERATOR_NOTES.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729/README.md
docs_followup: "Document ten-metric statutory observation staging, sparse projection, unit-kind preservation, and compatibility behavior."
reason: "The hash-pinned ASXFP programme declares Ticket 06 ready after Ticket 05, whose exact stacked head is reviewed and green."
task_tier: standard
---

# ASXFP Ticket 06 statutory observation projection

## Authority

- Stacked product base:
  `84295111c6ae400de4e6f1c6cd941a45a0f549a3`, the reviewed and exact-head
  green Ticket 05 branch head.
- Canonical ancestor:
  `b01885d6cd55242339662e91d18141aeb725f089`.
- Authoritative ticket:
  `.scratch/asx-financial-profile-extraction-recovery/issues/06-project-statutory-metrics.md`
  at SHA-256
  `3fec223fffa68a49384064d58ec8e6aa9c4a207b7a7b9f8cd2c08661faade7a4`.
- Authoritative specification SHA-256:
  `ecba77e0185fe5fe4d38c840624bb7da4ce5f4f6290458c7f6e2b33b3a8b8b67`.
- Authoritative plan SHA-256:
  `16ff026fa5cec820f9ce4cbe558b6fb4d168e6fc0e23c98854d81b1abf4b12ba`.
- Ticket 06 is declared `ready-for-agent` and blocked only by Ticket 05.

## Worker identity

- The worker's expected `HEAD` is the exact remote-pinned seed SHA supplied by
  the launcher as `CODEX_X_SOURCE_SHA`. It is later than the stacked product
  base only by this task card and report-local orchestration evidence.
- Verify `HEAD == CODEX_X_SOURCE_SHA`, verify the stacked product base is an
  ancestor, and verify the committed
  `84295111c6ae400de4e6f1c6cd941a45a0f549a3..HEAD` path set is limited to this
  task card and the allowlisted report files.
- Use the real Git binary with launcher-provided `GIT_DIR` and `GIT_WORK_TREE`
  only for read-only identity commands if the bound wrapper cannot append its
  audit log under the offline permission profile. Do not bypass the bound
  wrapper for mutation, staging, commits, or remote access.

## Objective

Promote exactly the existing ten `CANONICAL_METRIC_FIELDS` statutory metrics
through immutable observation persistence and deterministic profile reads,
without breaking current `ASXPeriodicFinancial` consumers or allowing a sparse
later extraction to erase previously accepted values.

The ten metrics are:

`revenue`, `ebit`, `np_attributable`, `operating_cf`, `investing_cf`,
`financing_cf`, `capex`, `cash_end`, `net_debt`, and `shares_outstanding`.

## Required behavior

- Expand the Ticket 05 observation seam from `revenue` to exactly those ten
  canonical metrics. Do not include persisted-only or planned metrics.
- Stage one immutable observation per accepted, present metric. Missing,
  ambiguous, non-numeric, non-statutory, unsupported-source, or insufficiently
  proven metrics must abstain independently without suppressing valid siblings.
- Keep source document, extraction run/version, ticker, metric, period end and
  basis, accounting basis, native currency or share unit, normalized absolute
  units, source-bound field provenance, and accepted trust state attached to
  each observation.
- Derive allowed statement contexts and unit kind from the authoritative
  financial metric contract. Currency-valued metrics retain native currency;
  `shares_outstanding` must retain a fail-closed share-count unit contract and
  must not be treated as money or FX-converted.
- Preserve Ticket 05 immutable identity, retry idempotence, PostgreSQL
  conflict-safe insertion, and caller-owned transaction behavior. The staging
  seam must not query before insert, call `add()`, `flush()`, `commit()`, or
  `rollback()`.
- Add a forward-only stacked Alembic migration that expands the closed metric
  vocabulary. Do not edit the already-published `0010` migration and do not
  execute either migration.
- Project uncontested accepted statutory observations for all ten metrics into
  the existing `/financials` response shape. Preserve the legacy row as the
  compatibility substrate and fallback.
- Overlay each metric independently only when observation currency/unit and
  absolute scale match the legacy row context. A missing later observation
  must leave the existing legacy metric intact.
- If accepted observations conflict for one metric at the same read identity,
  abstain only for that metric. Do not choose by insertion order, extraction
  run, UUID, or timestamp, and do not disturb other uncontested metrics.
- Keep public service naming compatible where practical, with narrow aliases if
  needed for existing Ticket 05 callers and tests.

## Hard stops

- Do not access any source PDF, protected label, diagnostic/holdout corpus,
  release manifest, local diagnostic output, or protected metadata.
- Do not run extraction, OCR, a model or prompt, evaluation, runtime, service,
  database or migration execution, queue, Qdrant, GPU, deployment, activation,
  canary, backfill, or production-data action.
- Tests must use pure fakes/mocks and must not create or connect to a database.
- Do not edit outside `allowed_files`.
- Do not merge, deploy, activate, close issues, or mark a PR ready.
- Do not add adjusted results, derive new financial metrics, perform FX
  conversion, expand period-basis semantics, select restatements, or retire
  legacy direct writes. Tickets 07–10 and 15 own those changes.

## Worker protocol

- Use one fresh Codex X implementer session.
- Validate this task card before product edits.
- Work test-first and record focused RED/GREEN evidence without a database.
- Freeze the exact delta after implementation.
- Use a different fresh Codex X session for independent read-only review.
- The parent Codex owns acceptance, commit, push, and stacked draft-PR
  publication.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket06_statutory_projection_v1_20260729.md`
- Focused RED/GREEN tests in
  `financial-engine_v2/backend/tests/test_financial_observations.py`.
- Existing focused pipeline/API/metric-contract tests that do not connect to a
  database.
- Alembic migration import/AST/structure inspection only; do not run
  migrations.
- Ruff for changed Python.
- `python3 -m py_compile` for changed Python.
- `git diff --check`.
- Task-card `check-diff`.
- Confirm no PDF, binary, protected corpus artifact, or runtime output is
  staged.

## Closeout

Return exact stacked base, branch, candidate tree, changed files, RED and GREEN
commands, validation status, reviewer verdict, remaining risks, and docs
impact. Publication may create a stacked draft PR against the Ticket 05 branch
only; merge and any database-backed proof remain separate approvals.
