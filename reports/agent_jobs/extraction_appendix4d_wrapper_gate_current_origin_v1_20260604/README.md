# Appendix 4D/4E Wrapper Gate Current-Origin Rebuild

Branch:
`safe/extraction-appendix4d-wrapper-gate-current-origin-v1-20260604`

Base:
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`78b111f423ee86fd1fdfc214f1db551576ee14f5`.

Reference:
parked commit `669d003026c68ce6ef667db7266f665f8a7dd7bd` inspected only as a
source for narrow wrapper-gate behavior. The parked branch was not merged or
rebased.

## Outcome

Implemented a narrow Appendix 4D/4E wrapper validation-gate exception:

- wrapper filings may pass with exactly two canonical metrics only when the two
  metrics are `revenue` and `np_attributable`;
- wrapper identity, source-bound period/scale/currency context, and required
  disclosure/control evidence must be present;
- NTA per security, dividends/distributions, record-date, and associate/JV rows
  remain disclosure-only and do not count as canonical metrics;
- ordinary annual and half-year reports retain the normal three-metric minimum.

No broad extraction, backfill, sample, canary, DB, Qdrant, news, memory, source
PDF, prompt, gold-label, runtime, schema, Cockpit, or registry deletion work was
performed.

## Targeted Simulation

`appendix4d_gate_simulation.json` records direct `_validate_gate` cases only.
The simulation did not open source PDFs or run extraction:

- wrapper with two canonical metrics plus disclosures: `ok`;
- wrapper missing disclosures: failed with
  `validation_gate:wrapper_missing_disclosure_evidence`;
- wrapper missing source-bound scale: failed with
  `validation_gate:wrapper_missing_source_bound_context`;
- disclosure-only metric keys: failed with `validation_gate:insufficient_metrics:1`;
- ordinary half-year with two metrics: failed with
  `validation_gate:insufficient_metrics:2`;
- ordinary annual with two metrics: failed with
  `validation_gate:insufficient_metrics:2`.

## DATA_MISSING

No source PDF was validated in this task by design. The requested gate validation
was targeted and synthetic; exact-PDF extraction behavior remains
`DATA_MISSING` until a separate approved targeted PDF validation is run.
