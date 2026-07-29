---
job_id: asxfp_ticket08_appendix4c_cash_profile_v1_20260730
title: Deliver the Appendix 4C quarterly cash profile for ASXFP Ticket 08
lane: Financial Truth
supporting_lanes:
  - Extraction
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "The owner explicitly requested one bounded Codex X Ticket 08 worker attempt."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_ticket08_appendix4c_cash_profile_v1_20260730
closeout_scope: local_commit
allowed_files:
  - docs/agent_tasks/asxfp_ticket08_appendix4c_cash_profile_v1_20260730.md
  - docs/extraction/appendix4c_cash_profile_contract.md
  - financial-engine_v2/backend/app/services/asx_appendix4c_parser.py
  - financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket08_appendix4c_cash_profile_v1_20260730/README.md
docs_impact: DOCS_REQUIRED
docs_checked:
  - docs/extraction
docs_changed:
  - docs/agent_tasks/asxfp_ticket08_appendix4c_cash_profile_v1_20260730.md
  - docs/extraction/appendix4c_cash_profile_contract.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/README.md
  - reports/agent_jobs/asxfp_remaining_tickets_codex_x_goal_v1_20260729/STATE.md
  - reports/agent_jobs/asxfp_ticket08_appendix4c_cash_profile_v1_20260730/README.md
docs_followup: "Document the isolated cash-profile result, evidence gates, deterministic precedence, and fallback boundary."
reason: "Ticket 08 is ready on the exact accepted Ticket 07 descendant supplied by the Codex X launcher."
task_tier: standard
---

# ASXFP Ticket 08 Appendix 4C quarterly cash profile

## Authority

- Exact product base commit:
  `dc4e99e305218dfea072e9c78cb13476dc6899fe`.
- Exact product base tree:
  `cb80b0320c3b3293c1182ae926f57baa5d21bdb6`.
- Authoritative ticket:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/.scratch/asx-financial-profile-extraction-recovery/issues/08-appendix-4c-cash-profile.md`
  at SHA-256
  `75f62f979076014333a8c958e8a085c0639b76fad8f5df65542cae02355b6dca`.

## Objective

Extend the existing standalone, table-only Appendix 4C parser into a focused
quarterly cash profile supporting customer receipts, operating, investing and
financing cash flow, capex, ending cash, unused financing, and estimated
funding quarters.

## Required behavior

- Exact Appendix 4C row mappings run before any fallback candidate is
  considered.
- The only fallback seam accepts explicit caller-supplied candidates; this
  module never invokes extraction, OCR, a model, runtime, or persistence.
- Fallback is constrained to supported profile fields, missing deterministic
  fields, exact current-quarter/YTD column roles, and allowlisted source line
  items.
- Every accepted profile value carries exact row/cell evidence plus explicit
  period, currency, and scale evidence. Ambiguous or missing evidence abstains.
- Current-quarter (`period_only`) and YTD (`year_to_date`) observations remain
  distinct and never overwrite each other.
- Appendix 4C input never infers or emits revenue, profit/NPAT, or net debt.
- Existing parser compatibility and report-local `canonical_write=false`
  behavior remain intact.

## Hard stops

- Do not access PDFs, protected labels, holdouts, diagnostic corpora, release
  manifests, or protected metadata.
- Do not run extraction, OCR, models, evaluation, runtime, services,
  databases, migrations, queues, Qdrant, GPUs, deployments, activation,
  canaries, backfills, or production writes.
- Do not edit outside `allowed_files`.
- Do not push, publish, open a PR, merge, or alter shared state.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_ticket08_appendix4c_cash_profile_v1_20260730.md`
- Focused pytest for `financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py`.
- Ruff and `python3 -m py_compile` for changed Python.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asxfp_ticket08_appendix4c_cash_profile_v1_20260730.md`.

## Closeout

Record exact changed files, validation commands and results, local commit/tree
if committed, docs impact, prohibited-action compliance, and remaining risks.

## Rejection repair

The rejected candidate repair starts from exact commit
`0879ff320cedc3a36ab962cea248d1fc2a04c253` / tree
`13b362907caaa55cbd00cbe77faa2d7b43108098`. Fallback evidence must be
authenticated against the referenced caller table, and deterministic
duplicates must be grouped into stable-equivalent selection or explicit
conflict abstention. Independent re-review remains pending.
