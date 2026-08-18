# Extraction Eval Foundation Combined Integration Prep

Generated: 2026-05-27T03:28:20Z

## Summary

Prepared an isolated integration-prep branch that reconciles the four validated
safe-extension commits for #97, #98, #99, and #96 without modifying canonical.

- Base canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Base canonical HEAD: `23ee2666f9d037c4405f4c97dac4f33b089523f1`
- Combined branch: `safe/extraction-eval-foundation-combined-v1-20260527`
- Worktree: `/home/l4nd0/tenn-extraction-eval-foundation-combined-v1-20260527`
- Task card:
  `docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md`
- Registry status: claimed under shared registry, no overlapping active jobs at
  preflight.

## Source Commits Reconciled

- #97 payload scorecard builder:
  `bb833aa8f916806e7151d0a49a094592644db418`
- #98 contract parity guard:
  `d08a3e96d61d8315491f5efbea61134bbd7735f6`
- #99 source asset manifest/resolver:
  `8f87683c87306267d8280704bf6a0116f4183096`
- #96 terminal extraction candidate manifest:
  `2f7af32d81d677dfd4eb213bc140c005b5b79e35`

## Conflict Cause And Resolution

The known conflict was real: #97 and #98 independently edited
`extraction_gold_eval_scorecard.py` and
`test_extraction_gold_eval_scorecard.py` from the same base. #99 also touched
the same helper/test, and #96 builds on #99.

Resolution used #96/#99 as the source-asset and terminal-state base, then
inserted the #97 payload scorecard API and the #98 metric contract parity API as
separate cohesive sections. Shared fixture-loading, expectation, and evaluator
helpers remain single-copy. The combined test file preserves the focused
synthetic coverage from all four branches.

## Files Changed

- Task cards for the combined prep job and the four source jobs.
- Source reports for #97, #98, #99, and #96.
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/eval_source_assets/README.md`
- `financial-engine_v2/backend/tests/eval_source_assets/confirmed_metric_coverage_source_assets.json`
- This report bundle.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md`
  - Result: passed, `ok: true`.
- `python3 scripts/agent_job_registry.py list-active --read-only`
  - Result: passed, `active_jobs: []`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
  - Result: passed, `ok: true`.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
  - Result: passed, shared registry claim active.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
  - Result: passed.
- `PYTHONPATH=financial-engine_v2/backend pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
  - Result: not run, host shell has no `pytest`.
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
  - Result: failed, `5 failed, 18 passed`; the failure was missing
    `sqlalchemy` in the ephemeral dependency set.
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 --with sqlalchemy pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
  - Result: passed, `23 passed, 1 warning`.
- `uv run --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
  - Result: passed, `All checks passed!`.
- `git diff --check && git diff --cached --check`
  - Result: passed.
- Raw PDF staging check: `git diff --cached --name-only | rg '\.pdf$' || true`
  - Result: passed, no `.pdf` paths staged.

- JSON validation for generated artifacts
  - Result: passed, `validated_json_files=19`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
  - Result: passed, `ok: true`, `disallowed_files: []`,
    `changed_count: 33`.

Registry release, final clean status, and commit SHA are recorded in the
closeout response after commit creation.

## Confirmed

- Canonical checkout was clean before the isolated worktree was created.
- All four source commits exist.
- The source commit file surfaces are task-card/report/eval helper/test/source
  asset metadata only.
- The combined branch preserves all four requested capabilities:
  payload scorecard, contract parity matrix, source asset resolver, and terminal
  extraction candidate manifest.
- No extraction/backfill, DB write, Qdrant/news/memory mutation, source PDF
  mutation, prompt/routing/gold-label change, service restart, runtime/GPU
  config change, Cockpit UI change, or schema migration was performed.

## Inferred

- The source commits should be superseded for canonical integration by this
  combined branch because it resolves their shared helper/test conflicts in one
  reviewed branch while preserving their report evidence.

## Speculative

- None.

## DATA_MISSING

- No live DB inspection was performed and production data access stayed false.
- No broad extraction/backfill/canary was run.
- The report file cannot embed the eventual self-referential commit hash before
  commit creation; the closeout response records the final immutable HEAD.

## Integration Readiness

Ready for canonical integration review after final validation and commit, with
the explicit boundary that this branch is report-local/eval-only and does not
authorize broad backfill.

## Project Memory

Recommended memory save: record that #96-#99 are reconciled by
`safe/extraction-eval-foundation-combined-v1-20260527`, and that the #97/#98
conflict was resolved by preserving both APIs in
`extraction_gold_eval_scorecard.py`.
