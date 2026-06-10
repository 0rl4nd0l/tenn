---
job_id: extraction_whc_parser_openability_sidecar_v1_20260610
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_parser_openability_sidecar_v1_20260610.md
  - financial-engine_v2/backend/app/services/docling_extract.py
  - financial-engine_v2/backend/tests/test_docling_extract.py
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/README.md
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/status.json
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/live_git_status.json
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/code_review.json
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/validation.json
  - reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_parser_openability_sidecar_v1_20260610
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# WHC Parser Openability Diagnostic Sidecar

## Objective

Move the WHC extraction blocker one production step forward by adding a bounded,
opt-in parser/openability diagnostic sidecar to `docling_extract.py`.

The sidecar may preserve statement-page OCR/text/table-cell candidates as
provenance diagnostics, but it must not feed canonical metric extraction,
selected statement tables, row refs, metric source scales, or validation gates.

Target evidence:

- Ticker: WHC
- Document id: `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- Prior report-local probe:
  `reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/`
- Existing saved-artifact finding: WHC source/OCR evidence has statement rows
  and `$000` scale evidence, while saved PyMuPDF cache preserves statement-page
  table geometry but zero nonempty statement cells.

## Allowed Repair Shape

- Add an explicit opt-in diagnostic path in `docling_extract.py`.
- Preserve diagnostics under a provenance-only field or sidecar structure that
  canonical consumers do not read.
- Keep default extraction behavior unchanged.
- Add focused mocked tests in `test_docling_extract.py`.
- Use dependency-injected command runners or pure functions for OCR/openability
  tests; do not require live OCR binaries in unit tests.

## Hard Stops

- Do not modify `multipass_extraction.py`.
- Do not emit accepted canonical metrics from OCR/source diagnostic rows.
- Do not route diagnostic rows into `StructuredDocument.tables` by default.
- Do not change canonical metric contracts, validation gates, source-period
  binding, scale policy, prompt/gold/schema/runtime/model/GPU config, or service
  routes.
- Do not run extraction, count-24, count-32, random samples, broad extraction,
  backfill, full ticker-universe extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, production data,
  prompts, gold labels, runtime state, model config, or GPU config.
- Do not use PR #318 as a patch source.
- Do not clean, stash, reset, delete, rebase, merge, or touch unrelated dirty
  files.

## Required Tests

- Positive: an opt-in diagnostic call preserves OCR-derived statement label,
  period phrase, scale phrase, and row candidates without normalizing values.
- Positive: diagnostic payload round-trips through parser cache without changing
  `tables` or `sections`.
- Negative: default parser extraction does not run the diagnostic path.
- Negative: OCR command failure records `DATA_MISSING` and does not promote
  metrics.
- Negative: unbounded page requests are rejected.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_whc_parser_openability_sidecar_v1_20260610.md`
- Registry `list-active --read-only`.
- Focused pytest for `test_docling_extract.py`.
- `python3 -m py_compile financial-engine_v2/backend/app/services/docling_extract.py`
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_whc_parser_openability_sidecar_v1_20260610.md --repo-root . --no-write-report`
- Forbidden-surface audit proving only allowlisted files changed.

## Final Report Requirements

Report current branch/HEAD/worktree, PR #340 status, registry state, code-review
findings, files changed, tests and validation with exact results, canonical
negative controls, `DATA_MISSING`, forbidden actions not run, and the next
recommended task.
