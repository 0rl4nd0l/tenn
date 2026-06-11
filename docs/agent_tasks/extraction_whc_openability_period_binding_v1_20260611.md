---
job_id: extraction_whc_openability_period_binding_v1_20260611
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_openability_period_binding_v1_20260611.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/README.md
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/status.json
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/live_git_status.json
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/validation.json
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/exact_replay_after_fix.json
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/code_review.json
  - reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_openability_period_binding_v1_20260611
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# WHC Openability Period Binding

## Objective

Fix the exact WHC replay blocker:

`validation_gate:missing_period_end`

The previous exact replay proved that the openability selected-table bridge can
produce 9 non-null WHC metrics with source-bound row refs and thousands scale,
but `period_end` remains null because openability diagnostic period phrases are
not included in the existing source-period evidence detector.

## Allowed Repair Shape

- Add a narrow helper in `multipass_extraction.py` that extracts existing
  `parser_diagnostics["openability"].ocr_records[*].period_phrases`.
- Use those phrases as source text only when `openability_selected_tables=True`.
- Reuse existing `_detect_source_period_evidence` and
  `_detect_source_period_end_evidence` logic.
- Preserve validation gates, prompts, schemas, gold labels, runtime config, model
  config, source PDFs, parser cache behavior, and service routes.
- Add focused tests in `test_multipass_extraction.py`.

## Required Tests

- Positive: opt-in openability diagnostics phrase `For the year ended 30 June
  2022` binds `period_end=2022-06-30`.
- Positive: the WHC-style mocked pipeline with openability selected tables now
  passes existing gates with `period_end=2022-06-30`.
- Negative: default extraction does not use openability period phrases.
- Negative: ambiguous openability period phrases remain fail-closed.

## Hard Stops

- Do not change `docling_extract.py`.
- Do not change prompts, gold labels, schemas, canonical metric contracts,
  validation gates, runtime/model/GPU config, parser cache, or service routes.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker-universe extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, production data,
  prompts, gold labels, runtime state, model config, or GPU config.
- Do not use PR #318 as a patch source.

## Validation

- Task card validate.
- Registry `list-active --read-only`.
- Focused pytest for `test_multipass_extraction.py`.
- `py_compile` for `multipass_extraction.py`.
- `ruff` for modified code/tests.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface audit.

## Final Report Requirements

Report branch/HEAD/worktree, registry state, code-review findings, files
changed, tests and validation with exact results, negative controls, scorecard
gain if measured, `DATA_MISSING`, forbidden actions not run, and next
recommended task.
