# Extraction BHP Eval Draft PR V1

## Summary

Prepared a draft PR for branch
`safe/extraction-bhp-canary-gold-fixture-v1-20260529` targeting
`migration/clean-runtime-baseline-reconstruct-v1`.

This branch contains:

- BHP FY2025 #96 canary real-gold regression fixture.
- Eval assertion that the observed BHP canary payload abstains with
  `revenue:wrong`.
- Real-gold source path validation through the existing allowlisted ASX source
  resolver.

## Scope

Allowed GitHub mutation: draft PR creation only.

Forbidden and not performed:

- Ready-for-review PR creation.
- PR merge.
- GitHub issue comments, closes, labels, milestones, or body edits.
- Runtime reload, extraction, canary, backfill.
- DB/Qdrant/news/memory/source-PDF mutation.
- Parser route, prompt, schema, runtime/model/GPU/service, or Cockpit UI
  changes.

## Validation Before PR

Already passed on this branch:

- Full focused gold-eval pytest: `25 passed, 5 warnings`.
- Targeted Ruff on `test_extraction_gold_eval.py`: passed.
- `py_compile` for `test_extraction_gold_eval.py`: passed.
- Remote branch head verified at
  `b95ec6eab5d9a19d2a3c040a04019cbcec09d01c` before this draft-PR task.

## Result

Pending until draft PR creation and verification complete.
