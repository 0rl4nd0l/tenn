# Extraction AAU Period Fixture Integration V1

## Summary

- Related issue: #96
- Branch: `safe/extraction-aau-integrated-baseline-v1-20260529`
- Worktree: `/home/l4nd0/tenn-extraction-aau-integration-v1-20260529`
- Base HEAD: `d55a515376e2bd065be9c94843d07ccca06f99f2`
- Mode: SAFE EXTENSION
- Runtime extraction run: no
- Third canary run: no
- Broad backfill run: no
- Direct SQL/Qdrant/news/memory mutation: no
- Source PDF mutation/copy/staging: no
- Parser routing, prompt, schema, runtime/model/GPU/service changes: no

## Integrated Source Commits

- `cb496fc1` - `milestone(extraction): harden explicit period-end semantics`
- `eb6ba6a5` - `milestone(extraction): record period-semantics claim release`
- `365bbef7` - `milestone(extraction): capture AAU canary failure fixture`
- `1be18324` - `milestone(extraction): record AAU fixture claim release`

The commits were integrated onto the current clean baseline with no-commit
cherry-picks so the combined diff could be validated under this task card.

## Conflict Resolution

`docs/claude/STATE.md` had one content conflict because both source branches
added a top session note. The resolution preserves both notes:

- AAU missing-period-end hardening in
  `safe/extraction-period-semantics-aau-v1-20260529`
- AAU canary-failure fixture capture in
  `safe/extraction-aau-canary-gold-fixture-v1-20260529`

No code conflicts occurred.

## Combined Behavior

- `multipass_extraction.py` detects typed explicit period-end phrases such as
  `year ended 31 December 2025` in early source sections.
- Missing `period_end` is filled only from unambiguous explicit source evidence.
- Conflicting explicit source period-end evidence hard-blocks with
  `validation_gate:period_end_source_mismatch`.
- The AAU canary failure is represented as a hand-verified test-only real-gold
  fixture with source-backed period, currency, scale, revenue, NPAT, and
  cash-flow metrics.
- Real-gold eval now proves a source-backed AAU payload is trusted and the
  historical missing-period payload quarantines with
  `context_mismatch:period_end`.

## Validation

Completed before commit:

- Task-card validate, overlap check, and registry claim passed.
- Focused AAU period/eval regressions: `6 passed`.
- `test_extraction_pre_canary_truth_gates.py`: `13 passed`.
- `test_multipass_extraction.py`: `160 passed`.
- `test_extraction_gold_eval.py -k 'not test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist'`:
  `23 passed, 1 deselected`.
- Full `test_extraction_gold_eval.py`: `23 passed, 1 failed`; the failure is
  the known unrelated missing 10X source-PDF asset path.
- Targeted Ruff: passed.
- Targeted `py_compile`: passed.
- JSON validation for fixture and report artifacts: passed.
- `git diff --check`: passed.
- Targeted code-review pass found one period-type regression risk and fixed it
  before commit: explicit typed period-end evidence now also blocks conflicting
  payload `period_type`.
- Conflict-marker scan over staged paths: passed.
- Source PDF/rendered-image staging check: passed.
- Credential-pattern scan: passed.
- Task-card `check-diff`: passed.
- Final code-reviewer pass: no remaining findings.

## Known Unrelated Validation Gap

The full `test_extraction_gold_eval.py` file is expected to retain the existing
10X repo-relative source-PDF asset-path failure unless that separate source-asset
issue is fixed. This integration does not copy or stage source PDFs.

## Next Safe Step

After this integration branch is merged into the active baseline and the live
backend is verified to serve the integrated code, rerun AAU alone through the
approved single-document canary path. Continue the remaining third-canary
sequence only if AAU passes the extraction gate.
