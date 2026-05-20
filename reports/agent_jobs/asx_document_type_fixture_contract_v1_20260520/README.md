# ASX Document-Type Fixture Contract v1 Report

## Confirmed Facts

- Runtime preflight was run from `/home/l4nd0/tenn-runtime`.
- `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Active runtime branch at preflight: `migration/clean-runtime-baseline-reconstruct-v1`.
- Active runtime HEAD at preflight: `a624da6e133f`.
- Preflight runtime worktree had one unrelated untracked task card:
  `docs/agent_tasks/memory_remaining_review_packet_v1_20260520.md`.
- Implementation used clean sibling worktree
  `/home/l4nd0/tenn-asx-document-type-fixture-contract-v1-20260520`
  on branch `safe/asx-document-type-fixture-contract-v1-20260520` to avoid
  absorbing unrelated runtime dirt.
- Task-card validation passed.
- Shared registry showed one active Memory job and no overlapping Financial
  Truth, extraction, parser, or evaluation fixture job.
- Effective registry overlap check passed in the clean sibling worktree.
- Registry claim succeeded for
  `asx_document_type_fixture_contract_v1_20260520`.

## Inferred Facts

- The unrelated Memory task-card artifact in the runtime checkout was not
  source-code dirt and was outside this task's allowed files.
- The clean sibling worktree was the safer execution lane because this repo's
  diff checker treats unrelated untracked files as outside the active card.

## DATA_MISSING

- The exact runtime-root overlap command could not validate the newly created
  card after isolation because the card lives in the sibling worktree, not in
  `/home/l4nd0/tenn-runtime`. The effective overlap and claim used the same
  shared registry from the clean sibling worktree.

## Files Added

- `docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`
- `docs/asx_document_type_fixture_contract.md`
- `financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json`
- `reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/README.md`

## Fixture List

- `annual_report_basic.json`
- `half_year_report_basic.json`
- `appendix_4c_quarterly_cashflow.json`
- `appendix_4d_half_year_results.json`
- `appendix_4e_preliminary_final.json`
- `appendix_5b_mining_cashflow.json`
- `other_asx_announcement_investor_presentation.json`
- `unknown_low_signal.json`
- `ambiguous_appendix_4d_4e_abstain.json`
- `manifest.json`

## Fixture Schema Summary

Each fixture includes `fixture_id`, `document_id`, `ticker`,
`expected_document_type`, `expected_confidence_band`, `expected_abstain`,
`source_text_surrogate`, `positive_anchors`, `negative_anchors`,
`required_evidence`, `abstain_reasons`, `must_not_infer_metrics`,
`canonical_write`, and `notes`.

The surrogate text is intentionally small and synthetic. It is classification
metadata only, not source truth for financial metrics.

## Document-Type Coverage

Covered document types:

- `annual_report`
- `half_year_report`
- `appendix_4c`
- `appendix_4d`
- `appendix_4e`
- `appendix_5b`
- `other_asx_announcement`
- `unknown_or_abstain`

## Abstain Cases

- `unknown_low_signal`: low-signal generic update with no supported report or
  Appendix form anchor.
- `ambiguous_appendix_4d_4e_abstain`: conflicting Appendix 4D and Appendix 4E
  anchors with mixed period language.

## Tests Run And Exact Results

- `python3 -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
  - Result: failed because system Python has no `pytest` module.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
  - First result: `1 failed, 8 passed, 1 warning`; the failing assertion was a
    whole-word test bug matching `nta` inside `commentary`.
  - Final result after test fix: `9 passed, 1 warning in 0.03s`.
  - Warning: transient uv pytest environment reported unknown repo pytest config
    option `asyncio_default_fixture_loop_scope`.
- `for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done`
  - Result: passed.
- `git diff --check`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`
  - Result: passed; `ok=true`, `disallowed_files=[]`, `issues=[]`.

## Safety Boundary Confirmation

- No classifier implementation module was added.
- No parser routing was changed.
- No extraction, Docling, OCR, comparator, Qdrant, news, memory, Cockpit, Home,
  runtime/model/GPU, DB, canonical write, gold label, or scorecard job was run
  or modified.
- Every fixture has `canonical_write=false`.
- Appendix 4C and Appendix 5B fixtures explicitly forbid revenue, NPAT, net
  debt, and income-statement metric inference.
- Appendix 4D and Appendix 4E fixtures treat EPS, NTA, and dividends only as
  review-only unsupported context.

## What This Enables Next

- A future pure classifier module can be implemented against the fixture shape.
- Unit tests can compare classifier output to fixture expectations.
- Read-only comparator artifact schemas can reuse `canonical_write=false`.

## What This Does Not Enable

- Parser routing.
- Canonical writes.
- Metric extraction.
- Gold-label or scorecard changes.
- Production data access.

## Final Git Status

- Pre-commit status is limited to allowed files for this task card. Final
  post-commit status is captured in the operator closeout.

## Registry Release Status

- Claimed successfully. Release is performed after commit so the final
  post-release registry state can be captured in the operator closeout without
  mutating production data.

## Commit Hash If Committed

- Pending at report draft time; final commit hash should be captured in the
  operator closeout after commit.

## Project Memory Save Recommendation

Save that ASX document-type fixture/schema contract v1 established a
fixture-only metadata boundary with `canonical_write=false`, synthetic anchors,
Appendix 4C/5B no-income-statement inference tests, Appendix 4D/4E
review-only unsupported metric context, and abstain cases for low-signal and
conflicting 4D/4E evidence.
