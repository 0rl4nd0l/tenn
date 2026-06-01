# Extraction Broad Residual Noncandidate Filter V1

## Summary

This task hardens the residual source-document classes exposed by the
post-candidate-scale-followup broad extraction sample. It does not run runtime
extraction, canary/process-document execution, backend/router/worker startup,
datastore writes, source-PDF mutation, parser prompt/schema changes, Cockpit UI
changes, or GitHub mutation.

Read-only source inspection classified the sampled residual failures as
non-candidate documents:

- LM8: `baker-rc-programme-results-complete` is a drilling/programme-results
  announcement without formal financial statements.
- LSR: `results-of-2022-agm` is an AGM result notice using the abbreviation
  `AGM`.
- LSF: `monthly-report-march-2022` is a monthly fund/performance report without
  formal Appendix or financial-statement evidence.
- OLY: `annual-asx-shareholder-summary` is standalone additional ASX
  shareholder information without formal financial statements.

## Implementation

- `multipass_extraction.py` now classifies AGM-abbreviation result notices as
  `meeting_results_notice`.
- `multipass_extraction.py` now classifies drilling/programme, monthly fund,
  and shareholder-summary/additional-ASX-information updates without formal
  Appendix or financial-statement evidence as
  `non_financial_update_without_formal_statements`.
- Explicit A/H/Q period-report evidence remains an allow signal so a quarterly,
  half-year, or annual report title is not excluded merely because it also
  mentions drilling results.
- Focused tests cover the four residual sampled classes and preserve formal
  Appendix 5B plus period-report eligibility.
- The broad extraction helper test now excludes these residual classes before
  sampling.

## Evidence Boundary

This is a deterministic candidate-filter improvement and reduces the rate at
which non-financial ASX announcements are sent into metric extraction. It is not
runtime proof, gold accuracy proof, direct canonical-row repair, broad backfill,
or full ticker-universe extraction graduation.

Next safe step: run a fresh approved bounded broad robustness runtime sample to
measure the new failure distribution.
