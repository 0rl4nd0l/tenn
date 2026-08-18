---
job_id: extraction_scale_source_unit_row_fix_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_scale_source_unit_row_fix_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/README.md
  - reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/status.json
  - reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/validation.json
  - reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
---

# Scale Source Unit Row Fix

## Objective

Add one focused parser/table coverage hardening for issue #96: selected
statement tables whose explicit source-unit row appears just below fragmented
heading rows must bind table-local scale instead of remaining
`scale_unknown`.

## Source Evidence

Current issue #96 evidence names the targeted scale-table/source-evidence
family. The fixed harness preserved AZJ
`488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` as a prior
`validation_gate:scale_unknown` sample where selected statement tables exposed
`$m` unit rows, but table-local scale stayed `unknown` in the diagnostic
artifacts:

- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/`

Later AZJ isolated replay normalized the same document to `ok`; this task is
therefore a narrow regression guard and parser/table robustness fix, not a
claim that the current exact AZJ replay is still failing.

## Allowed Repair Shape

- Add a focused red regression test for a selected statement table with
  fragmented heading rows and a source-unit row such as `Notes | $m | $m` below
  the first three rows.
- Extend deterministic table-local scale detection only enough to inspect a
  small selected-table head window for explicit unit-only scale rows.
- Preserve fail-closed behavior for tables without explicit scale evidence.
- Preserve validation gates, prompts, gold labels, schemas, runtime config,
  source PDFs, DB/Qdrant/news/memory, and broad extraction behavior.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, backfill, or
  full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime state, model/GPU config, or production data.
- Do not infer scale from ticker, filename, announcement date, value magnitude,
  or nearest-rounding policy.
- Do not reopen the closed AZJ same-page repair path as a broad production
  claim.

## Validation

- Task-card validate.
- Registry read-only check.
- Focused pytest for the new scale detector tests.
- `py_compile` for `multipass_extraction.py`.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.

## Final Report Requirements

Report the source evidence, exact files changed, focused validation results,
unsafe actions avoided, and whether PR was opened.
