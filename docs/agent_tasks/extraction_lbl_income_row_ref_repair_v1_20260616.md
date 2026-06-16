---
job_id: extraction_lbl_income_row_ref_repair_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/README.md
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/status.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/validation.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/live_git_status.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/evidence_summary.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/red_test.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/green_test.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/py_compile.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/ruff.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_stdout.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_stderr.log
  - reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# Extraction LBL Income Row Ref Repair

## Objective

Implement one bounded LBL income-statement `row_ref` provenance repair for
LBL-style presentation income tables. The repair must preserve or extract
source-bound row refs for `revenue`, `ebit`, and `np_attributable` when the
runtime has already found the correct values and source table, but the accepted
payload carries `row_ref: unknown`.

## Scope

Worktree:
`/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616`.

Branch:
`safe/extraction-lbl-income-row-ref-repair-v1-20260616`.

Base:
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`85250db58bc4ebd5b3e46790311afc7ec7e5b910`.

Mode: SAFE_EXTENSION / STRICTLY BOUNDED / RED-GREEN.

## Input Evidence

- Bounded LBL runtime report:
  `/home/l4nd0/tenn-lbl-bounded-runtime-execution-v1-20260616/reports/agent_jobs/extraction_lbl_bounded_runtime_execution_v1_20260616/`.
- The runtime accepted seven non-null metrics and resolved period/scale, but
  strict source-bound acceptance failed because `revenue`, `ebit`, and
  `np_attributable` row refs were `unknown`.
- The same evidence packet captured the income table markdown on page 21 with
  row labels `Sales Revenue`, `EBIT`, and `NPAT For` for those metrics.

## Required Implementation

- Add focused RED tests before implementation.
- Keep the implementation in
  `financial-engine_v2/backend/app/services/multipass_extraction.py`.
- Repair only table-local row-ref preservation/extraction for LBL-style
  presentation income tables.
- Fill `row_refs` and structured `field_provenance` for:
  - `revenue` from `Sales Revenue`
  - `ebit` from `EBIT`
  - `np_attributable` from `NPAT For`
- Preserve the existing values, period, scale, currency, source table, page, and
  validation-gate behavior.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, backfills,
  full ticker extraction, or canonical writes.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, runtime config, model config, GPU config, or production
  data.
- Do not make GitHub write actions.
- Do not broaden the fix into generic ontology expansion, prompt changes,
  schema changes, or runtime/service configuration.
- Stop if the row labels cannot be derived from the source table text.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`
- Focused RED test command before implementation.
- Focused GREEN test command after implementation.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- Rerun only the single-document bounded LBL replay.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md --repo-root .`

## Reporting

Report current repo state, ledger `DATA_MISSING`, duplicate-work
classification, files touched, validation commands and exit statuses, unsafe
actions avoided, remaining risk, and next recommended prompt in
`reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/README.md`.
