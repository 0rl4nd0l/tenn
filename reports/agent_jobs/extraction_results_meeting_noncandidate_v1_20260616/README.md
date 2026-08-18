# Results Of Meeting Noncandidate Guard

State: DONE

## Objective

Move #96 forward with one bounded source-noncandidate extraction fix:
title-only `results of meeting` announcements now fail closed before parser
work as `source_noncandidate:meeting_or_proxy_notice`.

## Failing Sample / Class

Class: source-noncandidate.

Current #96 evidence says `MQR results-of-meeting is fixed locally but not yet
in origin/migration`. On fresh origin baseline
`e33a64a8ee9795535acf2bdc0bd2bcc0fd09eb18`,
`_detect_source_noncandidate_class("Results of Meeting", "")` returned `None`.

Existing source-noncandidate taxonomy already has the correct output class:
`meeting_or_proxy_notice`. This task extends that class only to the deterministic
title phrase `results of meeting`.

## Change

- Added a red regression for `results-of-meeting.pdf`.
- Added a financial-report control for `half-year-results.pdf`, proving generic
  financial `results` titles remain candidates.
- Added one phrase check to `_detect_source_noncandidate_class`.

## Red / Green Evidence

Red before code change:

```text
results-of-meeting.pdf -> unknown_document, expected meeting_or_proxy_notice
1 failed, 13 passed, 185 deselected
```

Green after code change:

```text
14 passed, 185 deselected
```

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_results_meeting_noncandidate_v1_20260616.md` - PASS
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` - PASS, no active jobs
- Focused source-document classifier pytest - red then green, final PASS `14 passed, 185 deselected`
- `python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py` - PASS
- `uv run --with ruff ruff check ...` - PASS
- `git diff --check` - PASS
- JSON validation for report artifacts - PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_results_meeting_noncandidate_v1_20260616.md --repo-root .` - PASS, no disallowed files

## Unsafe Actions Avoided

- No count-24/count-32.
- No random sample, broad extraction, backfill, or full ticker-universe run.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  runtime state, model/GPU config, or production-data mutation.
- No validation gate relaxation.
- No generic financial-results exclusion.

## Files Touched

- `docs/agent_tasks/extraction_results_meeting_noncandidate_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/README.md`
- `reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/status.json`
- `reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_results_meeting_noncandidate_v1_20260616/diff-check.json`

## Next Step

Open a PR against `migration/clean-runtime-baseline-reconstruct-v1`. Keep #96
open; this is one bounded source-noncandidate child slice.
