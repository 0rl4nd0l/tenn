# Extraction BHP Eval Branch Publish V1

## Summary

Prepared publication of local branch
`safe/extraction-bhp-canary-gold-fixture-v1-20260529` to `origin`.

The branch contains:

- BHP FY2025 #96 canary real-gold regression fixture.
- Eval assertion that the observed BHP canary payload abstains with
  `revenue:wrong`.
- Real-gold corpus source path validation through the existing allowlisted ASX
  source resolver.
- Report/task artifacts for the BHP fixture and source-path validation tasks.

## Validation Before Push

Passed before this publish task:

- Full focused gold-eval pytest: `25 passed, 5 warnings`.
- Targeted Ruff on `test_extraction_gold_eval.py`: passed.
- `py_compile` for `test_extraction_gold_eval.py`: passed.
- Task-card validate/check-overlap/check-diff for both implementation tasks:
  passed.
- No added source PDFs or binary data files were staged.

## Publish Scope

Allowed GitHub mutation: branch push only.

Forbidden and not performed in this task:

- PR creation.
- GitHub issue comments, closes, labels, milestones, or body edits.
- Runtime reload, extraction, canary, backfill.
- DB/Qdrant/news/memory/source-PDF mutation.
- Parser route, prompt, schema, runtime/model/GPU/service, or Cockpit UI
  changes.

## Result

Pending until the final push and remote-head verification complete.
