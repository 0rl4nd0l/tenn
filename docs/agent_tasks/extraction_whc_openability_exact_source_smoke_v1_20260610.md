---
job_id: extraction_whc_openability_exact_source_smoke_v1_20260610
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_openability_exact_source_smoke_v1_20260610.md
  - reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/README.md
  - reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/live_git_status.json
  - reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/exact_source_smoke.json
  - reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/validation.json
  - reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_whc_openability_exact_source_smoke_v1_20260610
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# WHC Openability Exact-Source Smoke

## Objective

Run one exact-source, read-only local smoke of the newly added opt-in WHC
parser/openability diagnostics against document
`9640d9f1-a45b-492d-8df5-9bad0f46431c`.

This task must not run canonical extraction, service routes, count samples,
broad extraction, backfill, or production cache writes. It may read the exact
WHC source PDF and write only report-local artifacts.

## Allowed Method

- Use the current local branch containing
  `extraction_whc_parser_openability_sidecar_v1_20260610`.
- Set `docling_extract.settings.data_root` to a report-local temporary cache
  directory before calling the parser.
- Call `extract_structured(..., backend="pymupdf", openability_diagnostics=True,
  openability_pages=[57, 58, 60, 61])` against the exact WHC source PDF.
- Record only the resulting provenance diagnostic summary and negative-control
  facts.

## Hard Stops

- Do not edit parser code in this task.
- Do not modify `multipass_extraction.py`.
- Do not run canonical extraction.
- Do not write production parser cache.
- Do not mutate source PDFs, DB, Qdrant, Redis, news, memory, prompts, gold,
  schema, runtime, model, GPU, or service state.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker-universe extraction, or service routes.
- Do not use PR #318 as a patch source.
- Do not push or open a PR.

## Validation

- Task-card validate.
- Registry read-only.
- Exact-source smoke exits 0 and writes report-local JSON only.
- JSON validation.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface audit.

## Decision

If the diagnostic captures statement pages, scale pages, and source row
candidates while preserving `feeds_canonical_output=false`, the next task should
be a separately carded selected-table integration slice. If it does not, stop
and park the parser sidecar as insufficient for WHC.
