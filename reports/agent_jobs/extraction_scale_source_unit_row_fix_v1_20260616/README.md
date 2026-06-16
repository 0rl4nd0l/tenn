# Scale Source Unit Row Fix

State: DONE

## Objective

Move issue #96 one concrete production-readiness step forward by hardening
parser/table scale inference for selected statement tables whose explicit
source-unit row appears below fragmented heading rows.

## Failing Sample / Class

Class: parser/table coverage, scale-table/source-evidence.

Source evidence:

- Issue #96 current comments keep the scale-table/source-evidence class open.
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/`
  records AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` as an earlier
  `validation_gate:scale_unknown` sample with selected statement pages showing
  `$m` evidence.
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json`
  shows AZJ pass3a markdown and selected-table head rows containing `Notes |
  $m | $m`, while `_scale` stayed `unknown` and `_scale_source` stayed
  `document` in that older failing capture.

Guardrail:

- Later isolated AZJ replay
  `reports/agent_jobs/extraction_azj_nsr_isolated_pass3a_replay_v1_20260608/`
  returned `status=ok` with table-local `millions`. This fix is therefore a
  regression/robustness hardening for the source-evidence shape, not a claim
  that exact AZJ is currently failing.

## Why This Class

After PR #346 and the later provenance/parser child slices, #286's remaining
work crosses persistence/schema boundaries. #97 remains blocked on approved
actual payload maps. #96 still has an extraction-only parser/table coverage
class that can be improved without DB, schema, prompts, gold labels, broad
samples, or backfills.

## Change

- Added a focused regression test for fragmented selected statement headings
  where an explicit source-unit row such as `Notes | $m | $m` appears below the
  first three rows.
- Extended `_detect_scale_from_table` to inspect the first eight selected-table
  rows only for explicit unit/header rows.
- The new logic does not infer scale from value magnitude, ticker, filename,
  announcement date, nearest-rounding policy, or arbitrary prose rows.

## Red / Green Evidence

Red before code change:

```text
test_scale_detects_fragmented_statement_unit_row_below_headings
AssertionError: assert 'unknown' == 'millions'
```

Green after code change:

```text
1 passed
5 passed
21 passed, 176 deselected
```

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_scale_source_unit_row_fix_v1_20260616.md` - PASS
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` - PASS, no active jobs
- Focused red test through `uv run ... pytest ...::test_scale_detects_fragmented_statement_unit_row_below_headings` - FAIL before code change as expected
- Same focused test after code change - PASS
- Adjacent scale detector controls - PASS, 5 passed
- Focused scale subset: `pytest ...test_multipass_extraction.py -k 'scale'` - PASS, 21 passed, 176 deselected
- `python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py` - PASS
- `uv run --with ruff ruff check ...` - PASS
- `git diff --check` - PASS
- JSON validation for `status.json` and `validation.json` - PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_scale_source_unit_row_fix_v1_20260616.md --repo-root .` - PASS, no disallowed files

## Unsafe Actions Avoided

- No count-24/count-32.
- No random sample, broad extraction, backfill, or full ticker-universe run.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  runtime state, model/GPU config, or production-data mutation.
- No validation gate relaxation.
- No AZJ broad same-page propagation repair.

## Files Touched

- `docs/agent_tasks/extraction_scale_source_unit_row_fix_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/README.md`
- `reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/status.json`
- `reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_scale_source_unit_row_fix_v1_20260616/diff-check.json`

## Next Step

Open a PR against `migration/clean-runtime-baseline-reconstruct-v1`. Do not
close #96; this is one bounded parser/table hardening slice.
