# Extraction PLS Large Annual Report Statement Evidence V1

## Summary

This task fixes the deterministic evidence gap behind the PLS-style large
annual report blocker from the 2026-06-01 bounded broad runtime sample. It does
not run extraction runtime, canary/process-document execution, backend/router/
worker startup, datastore writes, source-PDF mutation, parser prompt/schema
changes, Cockpit UI changes, or GitHub mutation.

Source evidence inspected read-only:

- PLS `2023-annual-report-incorporating-appendix-4e`
- Formal statement pages contain `For the year ended 30 June 2023`
- Formal statement tables contain smart-apostrophe `$’000` column units

## Implementation

- Formal statement table scans now look beyond the first 15 tables, but only
  when the table text has formal financial-statement context.
- Section-level scale detection now combines same-page section fragments, so
  split PyMuPDF text such as statement heading, period line, and `$’000` unit
  line can be interpreted together.
- Source-period detection now falls back to formal statement pages/tables when
  early front matter does not expose a typed period end.
- Pass 1 publication-date period ends are corrected only when unambiguous typed
  source-period evidence supplies the formal statement period end.

## Evidence Boundary

This is a deterministic extraction hardening slice. It should remove the known
PLS `scale_unknown`/publication-date source-period blocker, but runtime
improvement remains unproven until a fresh approved bounded broad sample runs.
It does not complete third-canary readiness or full ticker-universe extraction
graduation.
