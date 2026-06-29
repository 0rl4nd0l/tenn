# Handoff - Approved-15 Blocker Lanes

Status: PARTIAL

Worktree:
`/home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629`

Branch:
`safe/extraction-approved15-blocker-lanes-v1-20260629`

Base used:
PR #461 merge commit `265a0d5a8125254c099e391087724097d6200517`.

Current origin later advanced to
`b2adf891096f41d4ddef260b1c47fd9b5a8417a4`; inspected extraction allowlist
showed no extraction-scope drift from `265a0d5a` to current origin.

## Completed

- Created report-local task card and six lane packets.
- Completed read-only lane investigation for A-F.
- Implemented one narrow source-proven Lane A RMS fix.
- Added focused RMS regression test.
- Ran focused unit test, focused no-write RMS replay, and approved-15
  scorecard/gate rebuild.

## Code Change

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - Cash-flow statement text overlay now accepts
    `statementofcashflows` in addition to
    `consolidatedstatementofcashflows`.
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
  - Adds RMS formal `STATEMENT OF CASH FLOWS` regression.

## Validation Result

- Focused unit test: pass.
- Focused RMS no-write replay: pass; side-effect audit passed.
- Approved-15 scorecard: four RMS rows moved from
  `missing_expected_metric` to `present_correct`.
- Gate: still failed.

After RMS fix:

- `ambiguous_quarantined=73`
- `not_evaluated_no_actual_payload=18`
- `present_wrong_value=2`
- `missing_expected_metric=0`

## Remaining Work

Recommended next lane: QBE or BHP/MIN.

- QBE: source-proven formal statement revenue selection issue; focused replay
  currently fail-closed because note-heading revenue is too low.
- BHP/MIN: source-proven owner-attributable `np_attributable` precedence issue.
- DXS: park until parser/table debug proves a narrow consolidated-statement
  precedence rule.
- Ambiguous quarantine: policy/source evidence review, not extractor code.

## Boundaries Preserved

No DB, Qdrant, Redis, news, runtime/backfill, production data, source PDF,
gold-label, prompt, model, service, count-24/count-32, or GitHub issue mutation
was performed.

## Recommended Prompt

See `handoff/NEXT_GOAL.md`.
