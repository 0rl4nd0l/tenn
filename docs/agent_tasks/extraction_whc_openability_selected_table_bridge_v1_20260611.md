---
job_id: extraction_whc_openability_selected_table_bridge_v1_20260611
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_openability_selected_table_bridge_v1_20260611.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/README.md
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/status.json
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/live_git_status.json
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/code_review.json
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/validation.json
  - reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_openability_selected_table_bridge_v1_20260611
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# WHC Openability Selected-Table Bridge

## Objective

Move WHC from parser/openability provenance capture toward canonical-ready
selected-table coverage by adding one explicit opt-in bridge from
`StructuredDocument.parser_diagnostics["openability"]` into Pass 2/3a table
selection.

The bridge may construct synthetic statement tables from source-bound OCR
diagnostic rows only when diagnostics already exist on the `StructuredDocument`.
It must not enable OCR by default, must not run extraction samples, and must not
change canonical output for documents without opt-in openability diagnostics.

Target evidence:

- Ticker: WHC
- Document id: `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- Prior exact-source smoke:
  `reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/`
- Source diagnostic classification: `ocr_openability_provenance_gap`
- Statement pages with source evidence: 57, 58, 60
- Scale pages with source evidence: 57, 58, 61
- Parser statement-page table count: 10
- Parser statement-page nonempty cell count: 0

## Allowed Repair Shape

- Add a small helper in `multipass_extraction.py` that converts existing
  openability diagnostic rows into synthetic `DoclingTable` objects.
- Use the bridge only when an explicit `run_multipass_extraction(...)` opt-in
  requests openability selected tables.
- Preserve default `run_multipass_extraction` behavior.
- Preserve validation gates, canonical metric names, prompts, gold labels,
  schemas, service routes, runtime config, and parser cache behavior.
- Add mocked focused tests in `test_multipass_extraction.py`.

## Required Gates

- Diagnostics must have `schema=docling_openability_diagnostics_v1`.
- Diagnostics must have `provenance_only=true`, `feeds_canonical_output=false`,
  and `canonical_output_changed=false` before bridging.
- At least one explicit source-bound period phrase must exist on the statement
  record.
- Scale must be exactly bound from the statement page or another diagnostic page;
  no value-size inference is allowed.
- Only row candidates with `candidate_value_quality=financial_amount` may be
  converted into synthetic rows.
- The bridge must record provenance in table captions/headers so row refs and
  metric source scale remain auditable.

## Hard Stops

- Do not change `docling_extract.py`.
- Do not enable OCR/openability diagnostics by default.
- Do not promote diagnostics into canonical metrics without Pass 3a, Pass 4, and
  existing validation gates.
- Do not change canonical metric contracts, validation gates, period binding,
  scale policy, prompts, gold labels, schemas, runtime/model/GPU config, parser
  cache, or service routes.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker-universe extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, production data,
  prompts, gold labels, runtime state, model config, or GPU config.
- Do not use PR #318 as a patch source.
- Do not clean, stash, reset, delete, rebase, merge, or touch unrelated dirty
  files.

## Required Tests

- Positive: existing WHC-style openability diagnostics can create synthetic
  income statement, balance sheet, and cash-flow statement tables with exact
  source rows, period phrases, and thousands scale.
- Positive: opt-in `run_multipass_extraction` can route those synthetic tables
  through Pass 3a with mocked LLM responses and existing validation gates.
- Negative: default `run_multipass_extraction` does not request openability
  diagnostics and does not create bridge tables.
- Negative: missing period evidence prevents bridge table construction.
- Negative: missing scale evidence prevents bridge table construction.
- Negative: non-financial/low-confidence row candidates are ignored.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_whc_openability_selected_table_bridge_v1_20260611.md`
- Registry `list-active --read-only`.
- Focused pytest for `test_multipass_extraction.py`.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- `ruff` for modified code/tests.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface audit proving only allowlisted files changed.

## Final Report Requirements

Report branch/HEAD/worktree, PR #340 status, registry state, exact files
changed, selected-table bridge evidence, validation with exact results,
negative controls, observed scorecard gain if any, `DATA_MISSING`, forbidden
actions not run, and next recommended task.
