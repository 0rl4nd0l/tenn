# Issue #97 Payload Scorecard Status

Issue: https://github.com/0rl4nd0l/tenn/issues/97
PR: https://github.com/0rl4nd0l/tenn/pull/207
Issue comment: https://github.com/0rl4nd0l/tenn/issues/97#issuecomment-4594945604
Stacked base: PR #206
(`audit/issue98-current-branch-status-v1-20260602`) so the GitHub diff stays
narrow while `origin/migration/clean-runtime-baseline-reconstruct-v1` is behind
the local baseline.

## Summary

#97 should remain open. Current repo evidence proves the confirmed-metric
payload scorecard plumbing exists, and later canary evidence proves a bounded
seven-document source-reviewed scorecard passed after the ATM scale fix. It
does not prove the original #97 target: extracted-payload accuracy for the
approved confirmed metric coverage profile.

## Current State

- GitHub issue state: open.
- Labels include `state:data-missing`, `state:needs-review`,
  `lane:evaluation`, `lane:financial-truth`, `lane:provenance`, and
  `type:validation-gap`.
- No exact closeout PR was found for #97.
- PR #131 is related metric gate integration work but is draft and not a #97
  closeout.
- PR #206 is the #98 closeout PR and explicitly leaves #97 as follow-up work.

## What Is Proven

- `build_confirmed_metric_payload_scorecard()` exists in
  `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`.
- The scorecard has explicit result classes for correct, wrong, missing,
  abstain, quarantine, no actual payload, evidence, period, unit, currency, and
  scale outcomes.
- `scripts/extraction_gold_eval_scorecard.py` exposes
  `--profile confirmed_metric_payload`, `--actuals-json`, and
  `--include-pre-persistence-gate`.
- The payload actuals coverage gate fails closed on unmatched actual payload
  document ids instead of silently ignoring them.
- `scripts/export_extraction_run_actual_payloads.py` can export explicit
  accepted `extraction_runs` rows into the scorecard actuals-json shape without
  mutating SQLite or canonical truth.
- The post-ATM-scale-fix bounded canary rerun scored 7/7 source-reviewed
  fixtures trusted, with 42/42 metric expectations correct.

## What Is Still DATA_MISSING

- A full actual payload map for the approved confirmed metric coverage profile.
- A passing confirmed-metric payload gate for the current 15-fixture / 146-row
  confirmed metric coverage inventory.
- Approved threshold policy for the full confirmed metric payload profile.
- A source-reviewed expansion path that maps canary documents into the
  confirmed metric coverage profile without conflating canary proof with broad
  coverage proof.
- Product graduation evidence across the broader annual, half-year, 4D, and 4E
  document classes.

## Decision

Keep #97 open with a current status comment. The issue is advanced by current
builder/gate/exporter/canary-scorecard evidence, but its broad acceptance target
is not proven.

## Next Safe Step

Create a narrow source-review and fixture-bridge task that either:

- supplies actual payloads for the existing confirmed metric coverage fixtures,
  then runs `scripts/extraction_gold_eval_scorecard.py --profile
  confirmed_metric_payload --actuals-json ... --include-pre-persistence-gate`,
  or
- explicitly documents a smaller source-reviewed subset so the result cannot be
  mistaken for full confirmed metric coverage.

## Boundary

This task did not edit product code, backend/runtime/frontend files, parser
prompts, gold labels, source PDFs, DB, Qdrant, news, memory, canonical
financial truth, runtime units, model/GPU/service config, PR state, or issue
closure state.
