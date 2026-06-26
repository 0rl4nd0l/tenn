# Issue #225 Cockpit Preferences Route Guard

## Result

Implemented a narrow safe-extension fix for issue #225 from current canonical
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`7d6ab6c184332d5413700eb08e6790f530000942`.

## Changes

- Added `Depends(require_api_key)` to backend `PATCH /api/cockpit/preferences`.
- Kept `GET /api/cockpit/preferences` public/read-only.
- Added backend tests for missing/wrong-key denial before state mutation and
  matching-key success.
- Added shared route dependency coverage for `PATCH /api/cockpit/preferences`.
- Updated `patchCockpitPreferences()` to send the configured `X-API-Key`.
- Added API-client test coverage for preference patch header propagation.
- Documented the read/write preference access contract in
  `docs/architecture/19_backend_api_surface.md`.

## Status

Local backend validation passed. Local frontend Vitest could not run because
`cockpit-ui/node_modules/.bin/vitest` is missing in this worktree; no dependency
install was performed.

No runtime services, DBs, stores, source PDFs, extraction outputs, prompts, gold
labels, model/GPU/service config, or production data were mutated.
