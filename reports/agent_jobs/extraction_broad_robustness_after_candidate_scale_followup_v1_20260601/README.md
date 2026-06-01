# Extraction Broad Robustness After Candidate Scale Followup V1

## Summary

Ran one bounded broad extraction robustness sample against `/data/asx/docs`
after `181ff690` landed candidate-filter and Appendix 4C scale hardening. The
run used llama.cpp through the local router on `8001`, seed `20260601`, and
requested `8` documents.

This is robustness/status evidence only. It is not a gold accuracy result and
does not authorize canary promotion, canonical writes, broad backfill, or full
extraction graduation.

## Candidate Filter

- Input `financial_performance` PDFs: `28,633`.
- Candidate PDFs retained: `24,721`.
- Excluded before sampling: `3,912`.
- Exclusion reasons: `meeting_results_notice=2116`, `meeting_notice=1660`,
  `operational_update_without_formal_statements=81`,
  `advisory_only_document=50`,
  `unaudited_financial_update_without_formal_statements=5`.

## Result

- Documents sampled: `8`.
- Unique tickers sampled: `7`.
- Status distribution: `ok=3`, `ok_low_confidence=1`, `failed=4`.
- Success rate: `50.0%`.
- Failure classes: `validation_gate=3`, `classifier_low_confidence=1`.
- Runtime total: `684.5s`; max document time: `237.64s`.
- Successful documents averaged `6.0` non-null metrics.

## Failure Digest

- `LM8`: low-confidence classifier failure on a programme-results announcement,
  `0/10` metrics.
- `LSR`: runtime source-document gate blocked `results-of-2022-agm`; candidate
  filtering did not catch the title-only AGM abbreviation.
- `LSF`: `validation_gate:invalid_period_type:null` on a monthly report, with
  only `shares_outstanding` non-null.
- `OLY`: `validation_gate:scale_unknown` on an annual ASX shareholder summary,
  with only `shares_outstanding` non-null.

## Accepted Documents

- `CHN`: quarterly activities/cash-flow report, `ok`, `5/10` metrics,
  `scale=thousands`.
- `ATT`: annual report, `ok`, `6/10` metrics, `scale=units`.
- `AAM`: Appendix 5B cash-flow report, `ok_low_confidence`, `6/10` metrics,
  `scale=thousands`; non-AUD CAD warning preserved.
- `CHN`: annual report, `ok`, `7/10` metrics, `scale=thousands`.

## Boundaries

- Backend startup: false.
- Canary/process-document route: false.
- Real-gold eval route: false.
- Broad backfill: false.
- Database, Qdrant, news, memory, or canonical financial row mutation: false.
- Source PDF copy or mutation: false.
- Parser, prompt, schema, or model/GPU config change: false.
- Cockpit UI or GitHub mutation: false.

## Cleanup

Dedicated GPU activity token `49412c6252c2446881eb89c3c163cba9` was cleared.
The transient router unit was stopped. Ports `8000` and `8001` were closed
after shutdown, GPU-exclusive activity was inactive, and the GPU process guard
reported no llama-server processes.

## Next Safe Step

Implement the next narrow candidate-filter/classifier slice for AGM
abbreviations such as `results-of-2022-agm`, monthly-report period handling,
and shareholder-summary source-unit classification before another broad sample.
