# Thesis Audit First-Run Workflow Audit

## Summary

Issue #118 asked whether the first-run Thesis Audit screen leaves users without
enough guidance to select a report/source and run an audit. Current evidence
shows the route exposes ticker/focus/report/text inputs, coverage preflight,
source-role labels, read-only evidence summaries, and evidence-limited warnings.
The current empty state is terse but not a confirmed product blocker.

## Decision

- Close gate: `COMPLETED_WITH_EVIDENCE`
- Finding class: `NO_FOLLOWUP`
- Product remediation landed: NO. This was an audit issue.
- Follow-up required: NO

## Evidence

| Area | Current evidence | Result |
| --- | --- | --- |
| First-run controls | `thesis-audit-screen.tsx:663` renders ticker, focus, select report, Audit, coverage refresh, and Thesis Source text area controls. | PASS |
| Empty state | `thesis-audit-screen.tsx:816` renders `No audit loaded.` before a run. Browser evidence also shows `Run an audit to review claims.` | Expected state |
| Coverage preflight | `thesis-audit-screen.tsx:710` renders coverage status and errors; `thesis-audit.spec.ts:197` expects `Coverage: ready`. | PASS by inspection |
| Provenance/source labels | `thesis-audit-screen.tsx:760` displays report source role; `thesis-audit.spec.ts:203` checks `non_canonical_thesis_source`. | PASS by inspection |
| Evidence-limited guard | `thesis-audit-screen.tsx:787` displays `Evidence-limited result`; `thesis-audit.spec.ts:311` verifies the warning and missing categories. | PASS by inspection |
| Backend boundary | `financial-engine_v2/backend/app/routes/thesis_audit.py:255` and `:276` require API key for audit and coverage routes. | PASS |

## Boundary Compliance

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No invented thesis claims, fake evidence, or auto-saved thesis memory.
- No product code changed.

## Validation Notes

Local Vitest/Playwright execution was not available because `vitest` is missing
in this isolated worktree. Existing Playwright test files and Gemini browser
artifacts were inspected instead.
