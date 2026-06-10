---
job_id: extraction_whc_ocr_openability_probe_report_local_v1_20260610
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_ocr_openability_probe_report_local_v1_20260610.md
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/README.md
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/status.json
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/live_git_status.json
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/whc_ocr_openability_probe.py
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/test_whc_ocr_openability_probe.py
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/whc_ocr_openability_probe.json
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/validation.json
  - reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/diff-check.json
approval_required: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
---

# WHC OCR Openability Probe, Report-Local

## Objective

Implement a report-local OCR/openability provenance probe for exact WHC document
`9640d9f1-a45b-492d-8df5-9bad0f46431c`.

The probe may read saved artifacts and the exact WHC source PDF path, but must
not change canonical extraction output, parser cache, source PDFs, runtime
configuration, prompts, gold labels, schema, DB, Qdrant, Redis, news, or memory.

## Allowed Implementation

- Create a report-local Python harness under this job output directory.
- Create mocked focused tests for parsing, cache-gap classification, bounded-page
  enforcement, command failure handling, and report-local write enforcement.
- Produce one diagnostic JSON sidecar:
  `reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/whc_ocr_openability_probe.json`.

## Hard Stops

- Do not edit `financial-engine_v2/backend/app/services/docling_extract.py`.
- Do not edit `financial-engine_v2/backend/app/services/multipass_extraction.py`.
- Do not write parser cache.
- Do not emit accepted canonical metrics.
- Do not run extraction, count samples, broad extraction, backfill, or service
  routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime/service/model/GPU config, or production data.
- Do not use PR #318 as a patch source.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_whc_ocr_openability_probe_report_local_v1_20260610.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/test_whc_ocr_openability_probe.py`
- `python3 reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/whc_ocr_openability_probe.py --mode saved-evidence`
- `python3 -m py_compile reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/whc_ocr_openability_probe.py reports/agent_jobs/extraction_whc_ocr_openability_probe_report_local_v1_20260610/test_whc_ocr_openability_probe.py`
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_whc_ocr_openability_probe_report_local_v1_20260610.md --repo-root .`
- Forbidden-surface exact path audit.
