# Extraction Broad Candidate Filter And Scale Followup V1

## Summary

This bounded Financial Truth slice hardens deterministic source classification
and explicit table-unit detection for the next broad extraction blockers from
the post-hardening sample.

Implemented:

- Meeting notices and proxy forms are excluded before candidate sampling and
  metric extraction.
- Customer, contract, and revenue-update announcements without formal Appendix
  or financial-statement evidence are excluded.
- Appendix 4C cash-flow/business-update reports remain eligible.
- USD thousand headers such as `$USD'000` and smart-apostrophe equivalents are
  detected as `scale=thousands`.

Not performed:

- No runtime extraction, canary, process-document route, backend/router/worker
  startup, datastore write, source-PDF mutation, prompt/schema change, Cockpit
  UI change, or GitHub mutation.
- This is not full ticker-universe extraction graduation.

## Validation

- Focused source/scale tests: `8 passed, 184 deselected`.
- Focused broad-candidate helper test: `1 passed, 5 deselected`.
- Full touched test files: `198 passed`.
- Targeted Ruff: passed.
- `py_compile` on touched Python files: passed.
- Exact post-hardening failure probe: CCR/AAM/IXC excluded; IMR retained.
- No-runtime `/data/asx/docs` inventory probe: 28,633 total, 24,721
  candidates, 3,912 excluded.

## Next Safe Step

Run a fresh approved bounded broad robustness runtime sample to measure the
remaining failure distribution.
