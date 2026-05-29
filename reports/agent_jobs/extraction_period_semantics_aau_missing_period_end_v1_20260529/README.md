# Extraction Period Semantics AAU Missing Period End V1

## Summary

- Related issue: #96
- Branch: `safe/extraction-period-semantics-aau-v1-20260529`
- Worktree: `/home/l4nd0/tenn-period-semantics-aau-v1-20260529`
- Base HEAD: `d55a515376e2bd065be9c94843d07ccca06f99f2`
- Mode: SAFE EXTENSION
- Runtime extraction run: no
- Broad backfill run: no
- Direct SQL/Qdrant mutation: no
- Source PDF mutation: no
- Parser routing, prompt, schema, runtime/model/GPU/service changes: no

## Root Cause

The approved #96 third canary stopped on AAU
`508fc892-ae88-45ec-981f-cd9e124c8375` because Pass 1 produced
`period_type=A` with `period_end=null`. The existing validation gate correctly
failed the payload with `validation_gate:missing_period_end`.

The source PDF explicitly contains the period date in early front matter:

`FOR THE YEAR ENDED 31 DECEMBER 2025`

The previous extraction path only sent page-1 text to the classifier and had no
deterministic explicit-period fallback for this kind of front-matter phrase.

## Change

- Added deterministic detection for typed explicit period-end phrases:
  - `year ended <date>` -> annual period end
  - `half-year/six months ended <date>` -> half-year period end
  - `quarter/three months ended <date>` -> quarterly period end
- The extractor now scans early source sections for this document-level period
  evidence and fills `period_end` only when Pass 1 leaves it empty.
- Explicit source period-end evidence is carried in the payload as
  `source_period_end_evidence`.
- If Pass 1 supplies a period end that conflicts with unambiguous explicit
  source period-end evidence, the existing validation gate fails with
  `validation_gate:period_end_source_mismatch`.

The fix does not infer from publication date, filename, ticker, previous runs,
or datastore state.

## Repro And Validation

Failing repro before fix:

- `test_run_multipass_uses_explicit_front_matter_period_end_when_pass1_misses_it`
  failed with `validation_gate:missing_period_end`.

Passing validation after fix:

- `test_run_multipass_uses_explicit_front_matter_period_end_when_pass1_misses_it`,
  `test_explicit_source_period_end_conflict_is_hard_blocked`, and
  `test_explicit_source_period_end_detection_refuses_ambiguous_or_loose_dates`:
  `3 passed`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`:
  `12 passed`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`: `160 passed`
- Targeted Ruff on changed Python files: `All checks passed`
- Targeted `py_compile` on changed Python files: passed
- `git diff --check`: passed
- AAU PDF first-four-page helper probe detected:
  `period_type=A`, `period_end=2025-12-31`,
  `reason=year_ended_explicit_date`

## Next Safe Step

Do not resume the remaining third-canary documents directly from the failed run.
After this fix is integrated into the active baseline and the live backend is
serving it, rerun AAU alone through the approved single-document route. Only if
AAU passes the extraction gate should the canary continue to ATM, AM5, AQX,
CRS, CLV, and CTM in order.
