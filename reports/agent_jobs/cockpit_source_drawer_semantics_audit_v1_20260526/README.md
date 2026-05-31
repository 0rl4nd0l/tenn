# Cockpit Source Drawer Semantics Audit

## Summary

Issue #95 asked whether Cockpit could render weak, degraded, no-hit, or
context-only evidence as claim-verified support. Current repo evidence shows
the backend and UI preserve those distinctions. The audit resolves the original
`DATA_MISSING` state and classifies the finding as `NO_FOLLOWUP`.

## Decision

- Close gate: `COMPLETED_WITH_EVIDENCE`
- Finding class: `NO_FOLLOWUP`
- Product remediation landed: NO. This was an audit issue.
- Follow-up required: NO

## Evidence

| Area | Current evidence | Result |
| --- | --- | --- |
| Backend metadata | `financial-engine_v2/backend/app/routes/cockpit_api.py:3380` excludes `context_only` from claim-verified source counts, and `:3409` discards tool-level `claim_verified`. | PASS |
| Coverage state | `financial-engine_v2/backend/app/routes/cockpit_api.py:3436` orders degraded, missing, personal, claim-verified, financial-truth, no-hit, context-only, and no-visible-sources states explicitly. | PASS |
| UI shell labels | `cockpit-ui/components/cockpit/chat/terminal-message.tsx:268` shows `Evidence-bound` only for verified counts or evidence-bound classification, and `:301` falls back to `Context sources only` for non-verified sources. | PASS |
| Source rendering | `cockpit-ui/components/cockpit/chat/terminal-message.tsx:868` renders the inline source list and `:901` displays the source evidence label, kind, doc type, date, and document id. | PASS |
| Unit-test contract | `terminal-message.test.tsx:149` verifies no-hit audit sources are not called source-backed; `:183` verifies context-only is not source-backed financial facts; `:215` verifies financial-truth numeric context is not rendered as verified sources. | PASS by inspection |
| Browser regression contract | `cockpit-ui/tests/chat-browser-regression.spec.ts:574` verifies plain answers have no Sources/Trust shell, partial-evidence messages show source/gap metadata, and source lists close/reopen. | PASS by inspection |

## Boundary Compliance

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No source-label relaxation.
- No product code changed.

## Validation Notes

Local Vitest execution was attempted, but `npm --prefix cockpit-ui test -- ...`
failed because `vitest` is not installed in this isolated worktree. I did not
install dependencies because dependency installation and `node_modules` churn
are outside this report-only task. The audit decision is based on current static
source/test inspection plus existing browser-regression coverage.
