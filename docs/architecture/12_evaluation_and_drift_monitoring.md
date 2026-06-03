# Evaluation and Drift Monitoring

Appendix 4D/4E extraction should be verified with targeted regression tests, not broad sample runs.

## Appendix 4D/4E Alias Policy

- Explicit ordinary-activities profit-after-tax rows may map to `np_attributable`.
- Pre-tax and comprehensive-income rows must not map to `np_attributable`.
- NTA, dividends/distributions, and record-date disclosures remain non-canonical.
- Short Appendix 4D/4E wrapper documents may only relax the metric minimum when wrapper identity, wrapper disclosure evidence, and source-bound period/scale/currency context are all present.

## Validation Shape

- focused pytest
- deterministic contract checks
- no broad backfill or sample execution
