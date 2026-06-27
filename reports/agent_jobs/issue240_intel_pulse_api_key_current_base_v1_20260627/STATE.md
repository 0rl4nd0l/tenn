# State

- Branch: `safe/issue240-intel-pulse-api-key-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Issue: #240
- Superseded prior work: PR #435 is conflicting on current base and has a P2
  review finding about browser-stored Cockpit API keys.

## Changes

- Added `require_api_key` dependencies to `/api/cockpit/pulse` and
  `/api/cockpit/matrix`.
- Updated the shared Cockpit API client key helper to prefer browser
  `localStorage["cockpit.apiKey"]` before `NEXT_PUBLIC_API_KEY`.
- Sent `X-API-Key` from `getIntelPulse()` and `getDiagnosticMatrix()`.
- Added focused backend and frontend regressions.
- Documented guarded Intel Pulse route policy.

## Safety

- No DB, Qdrant, news store, memory store, source PDF, gold label, extraction
  prompt, runtime service, model, GPU, or production data mutation was performed.
- Intel Pulse service semantics and diagnostic matrix cell-state logic were not
  changed.
