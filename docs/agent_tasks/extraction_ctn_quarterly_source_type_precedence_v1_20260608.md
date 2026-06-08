---
job_id: extraction_ctn_quarterly_source_type_precedence_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_ctn_quarterly_source_type_precedence_v1_20260608.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/README.md
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/validation.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# CTN Quarterly Source-Type Precedence

## Objective

Implement one CTN-only source-period classifier precedence repair for exact
quarterly Appendix 5B evidence when an irrelevant body-text annual-report
reference currently causes `period_source_mismatch`.

Target record:

- CTN `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- Current gate:
  `validation_gate:period_source_mismatch:payload=Q:source=A:annual_report_title`
- Exact quarterly evidence:
  - Page 1: `Quarterly Activity Report` and `Period ending 31st March 2022`
  - Appendix 5B page 22: `quarterly cash flow report` and
    `Quarter ended ... 31/03/2022`
- Irrelevant annual hit:
  - Body text: `2014 Annual Report to Shareholders`, a historical-cost
    narrative reference, not the reporting-period heading.

## Source Audit Dependency

This task depends on the preserved report-only audit:

- Commit: `0d4c8925e0513d210edc3dcc8e34c6571f3acdda`
- Report:
  `reports/agent_jobs/extraction_period_source_exact_evidence_audit_v1_20260608/README.md`

The implementation branch is based on
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`5d5e1e7b29f16ca5d07d9bfafaea8dc8e98c9368`; the preserved audit commit is cited
as evidence and is not used as a patch source.

## Allowed Repair Shape

- Add a narrow source-period evidence rule so strong quarterly signals for
  `Quarterly Activity Report` / `Appendix 5B quarterly cash flow report` can
  dominate an isolated `annual_report_title` hit from non-heading body text.
- Preserve true annual-report detection.
- Preserve mixed annual/quarterly ambiguity when the annual signal is a real
  reporting-period/title signal, not a historical narrative reference.
- Do not change period_end from announcement date or title date.
- Do not change scale inference, metric contracts, canonical ontology, or
  validation gates outside this source-period evidence classification.

## Hard Stops

- Do not include HUB or LBL in this repair.
- Do not infer any period_end from fiscal labels.
- Do not accept announcement date, announcement title date, or generic document
  title date as period_end.
- Do not relax generic period mismatch quarantine.
- Do not run count-24, count-32, random samples, broad extraction, backfill,
  full ticker extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, runtime/service/model/GPU config, schema, or production data.
- Do not touch PR #326/news files.
- Do not use PR #318 as a patch source.

## Required Tests

- Positive: `Quarterly Activity Report` plus `Period ending 31st March 2022`
  and an irrelevant `2014 Annual Report to Shareholders` body reference returns
  source period type `Q`.
- Positive: Appendix 5B quarterly cash flow report text returns source period
  type `Q`.
- Positive: source document classification preserves the CTN quarterly report as
  a financial-report candidate.
- Positive: a Q payload with matching quarterly source-period evidence passes
  the period/source gate.
- Negative: true annual-report source text remains source period type `A`.
- Negative: real mixed annual-report title plus Appendix 5B/quarterly evidence
  remains ambiguous/fail-closed.
- Negative: explicit annual period-end evidence still hard-blocks a Q payload.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_ctn_quarterly_source_type_precedence_v1_20260608.md`
- Registry `list-active --read-only`.
- Focused unit test if the local Python environment can import backend
  dependencies.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_ctn_quarterly_source_type_precedence_v1_20260608.md --repo-root . --no-write-report`
- Forbidden-surface audit proving only allowed files changed.
