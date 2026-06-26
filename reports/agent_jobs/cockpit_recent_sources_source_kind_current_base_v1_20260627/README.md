# Cockpit Recent Sources Source Kind

Issue: #213

Branch: `safe/issue213-recent-source-kind-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@b92133455871f2a9be1f9030b2ef4abc995dfb9d`

Status: `DONE_WITH_RISK`

Summary:

- Added `source_kind` to recent commentary endpoint items using deterministic source-type mapping.
- Updated `SourcesDrawer` to carry `sourceKind` through `onReattach`.
- Updated chat reattach handling to use the drawer-provided source kind instead of hardcoding `ephemeral`.
- Added backend and drawer regression assertions.

Risk note:

- Local backend validation passed.
- Local Cockpit UI validation could not run because `cockpit-ui/node_modules/.bin/vitest` and `eslint` are absent; no dependency install was performed.
- GitHub CI should be treated as the frontend validation gate before merge.
