---
job_id: extraction_hub_period_end_binding_repair_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_hub_period_end_binding_repair_v1_20260608.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_hub_period_end_binding_repair_v1_20260608/README.md
  - reports/agent_jobs/extraction_hub_period_end_binding_repair_v1_20260608/validation.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_hub_period_end_binding_repair_v1_20260608
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# HUB Period-End Binding Repair

## Objective

Implement one HUB-pattern period-end binding repair: when Pass 1 uses the ASX
announcement title date as a half-year `period_end`, exact source-bound
half-year period-end text may override that title date before validation.

Target record:

- HUB `419bcca8-213e-4706-8962-8e3bd8adf091`
- Current gate:
  `validation_gate:announcement_date_period_end:period_type=H:period_end=2024-02-20:title_date=2024-02-20:leading_title_date`
- Exact source evidence:
  - `Half-year ended 31 December 2023`
  - `Current period: 1 July 2023 to 31 December 2023`
  - Same-page document header and table-local support on page 3.

LBL is explicitly out of scope. Its preserved evidence has `1H FY26` and
`Half-Year` labels only, with no exact source-bound period-end date.

## Source Audit Dependency

This task depends on the preserved report-only evidence audit:

- Report:
  `/home/l4nd0/tenn-extraction-period-source-exact-evidence-audit-v1-20260608/reports/agent_jobs/extraction_period_source_exact_evidence_audit_v1_20260608/evidence_audit.json`
- Preserved scorecard commit:
  `6e8be73cf5e16f8923d33f60ad7887c70aef1bd9`
- Repair closeout commit:
  `df821df661c1218d8155d6addaf44e3b3b9e6a14`

The implementation branch is based on current
`origin/migration/clean-runtime-baseline-reconstruct-v1`. The audit artifacts are
used as evidence only, not as a patch source.

## Allowed Repair Shape

- Bind `period_end` only from explicit source-bound half-year period-end text
  detected by typed reporting-period phrases such as
  `Half-year ended 31 December 2023`.
- Apply the override only when the existing Pass 1 `period_end` equals the
  leading announcement date in a half-year title.
- Require the payload/classifier period type and source period-end evidence type
  to both be `H`.
- Preserve the announcement-date-as-period-end hard guard for title-only and
  label-only cases.
- Preserve source period type and period-end mismatch gates.

## Hard Stops

- Do not include LBL in the positive repair path.
- Do not infer period end from `1H FY26`, fiscal labels, fiscal calendars, or
  generic `Half-Year` labels.
- Do not include CTN in this repair.
- Do not accept announcement date, announcement title date, or generic document
  title date as `period_end`.
- Do not relax generic period mismatch quarantine.
- Do not change canonical metric contracts, metric ontology, disclosure
  promotion, or scale inference.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, runtime/service/model/GPU config, schema, or production data.
- Do not touch PR #326/news files.
- Do not use PR #318 as a patch source.

## Required Tests

- Positive: HUB-style title date `2024-02-20` is overridden to `2023-12-31`
  only when exact `Half-year ended 31 December 2023` evidence is present.
- Positive: a valid HUB-style half-year payload with exact source period-end
  evidence passes the period/source and announcement-date gates.
- Negative: HUB title-date-only evidence remains blocked by
  `announcement_date_period_end`.
- Negative: LBL-style `1H FY26` / `Half-Year` label-only evidence remains blocked
  and does not infer `2025-12-31`.
- Negative: exact source evidence does not override a non-announcement-date
  payload period end.
- Negative: missing Pass 1 `period_end` is not filled from title-only explicit
  half-year period-end evidence.
- Positive: missing Pass 1 `period_end` is filled from parsed source-text
  half-year period-end evidence.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_hub_period_end_binding_repair_v1_20260608.md`
- Registry `list-active --read-only`.
- Focused unit tests for the period/source binding owner file.
- Negative-control tests for announcement-title-only and label-only fail-closed
  behavior.
- Saved-artifact replay against preserved HUB evidence only; no extraction.
- JSON validation for report artifacts.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_hub_period_end_binding_repair_v1_20260608.md --repo-root . --no-write-report`
- Forbidden-surface audit proving only allowed files changed.
