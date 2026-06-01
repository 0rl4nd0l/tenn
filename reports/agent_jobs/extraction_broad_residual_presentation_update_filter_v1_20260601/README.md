# Extraction Broad Residual Presentation Update Filter V1

## Summary

This task hardens the residual non-candidate classes exposed by the
post-residual-filter broad runtime sample. It does not run extraction runtime,
canary/process-document execution, backend/router/worker startup, datastore
writes, source-PDF mutation, parser prompt/schema changes, Cockpit UI changes,
or GitHub mutation.

Source-inspected residual failures addressed:

- CMM: `annual-general-meeting-presentation`
- MFG: `full-year-results-briefing-18-august-2023-at-11-30-am`
- CMM: `capricorn-raises-200m-to-underpin-growth`
- MFD: `launch-of-mayfield-360-allied-health-services`

## Implementation

- AGM/annual-general-meeting presentations are excluded as
  `non_financial_update_without_formal_statements`.
- Results briefing/presentation/webcast notices are excluded as
  `non_financial_update_without_formal_statements`.
- Capital-raising and placement announcements are excluded as
  `operational_update_without_formal_statements`.
- Product/service launch updates are excluded as
  `operational_update_without_formal_statements`.
- Formal Appendix, financial-statement, and explicit A/H/Q period-report
  evidence remain allow signals; PLS-style annual reports incorporating
  Appendix 4E stay candidates.

## Evidence Boundary

This is a deterministic candidate-filter improvement only. It reduces
non-candidate ASX announcements reaching metric extraction, but it does not fix
the PLS large annual report scale/source-period blocker, prove runtime success,
authorize canonical writes, or complete ticker-universe extraction graduation.
