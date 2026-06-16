# Webcast Details Noncandidate Guard

State: DONE

## Objective

Move #96 forward with one bounded source-document policy fix: webcast-details
logistics announcements no longer get promoted to financial-report candidates
just because their title includes `half-year results`.

## Failing Sample / Class

Class: source-noncandidate / document-family policy gap.

Current source evidence:

- Scale-table harness case: NIC
  `50398d3d-27f7-4d9e-8a26-a2d69f128a1c`.
- Source path title:
  `2025-08-11_half-year-results-webcast-details_50398d3d-27f7-4d9e-8a26-a2d69f128a1c.pdf`.
- Harness forbidden output: `webcast-details title promoted to financial report
  without exact source review`.
- Fresh baseline behavior before this fix:
  `classify_source_document("half-year-results-webcast-details.pdf", ...)`
  returned `financial_report` with `half_year_source_phrase`.

## Change

- Added source-noncandidate class `webcast_details_notice`.
- Added a focused regression for `half-year-results-webcast-details.pdf`.
- Preserved the existing `half-year-results.pdf` financial-report control.
- Updated source-document contract docs for the new narrow class.

## Red / Green Evidence

Red before code change:

```text
half-year-results-webcast-details.pdf -> financial_report, expected webcast_details_notice
1 failed, 14 passed, 185 deselected
```

Green after code change:

```text
15 passed, 185 deselected
```

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_webcast_details_noncandidate_v1_20260616.md` - PASS
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` - PASS, no active jobs
- Focused source-document classifier pytest - red then green, final PASS `15 passed, 185 deselected`
- `python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py` - PASS
- `uv run --with ruff ruff check ...` - PASS
- `git diff --check` - PASS
- JSON validation for report artifacts - PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_webcast_details_noncandidate_v1_20260616.md --repo-root .` - PASS, no disallowed files

## Unsafe Actions Avoided

- No count-24/count-32.
- No random sample, broad extraction, backfill, or full ticker-universe run.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  runtime state, model/GPU config, or production-data mutation.
- No validation gate relaxation.
- No generic financial-results or presentation-title exclusion.

## Files Touched

- `docs/agent_tasks/extraction_webcast_details_noncandidate_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `docs/extraction/metric_extraction_contract.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/README.md`
- `reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/status.json`
- `reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_webcast_details_noncandidate_v1_20260616/diff-check.json`

## Next Step

Open a PR against `migration/clean-runtime-baseline-reconstruct-v1`. Keep #96
open; this is one bounded source-document policy child slice.
