# Cockpit Mobile Chrome Compact

Issue: #46, `Cockpit production UI does not automatically switch to a mobile-safe layout on narrow viewports`

## Decision

Implement a narrow shared-shell first slice. This does not claim full route-level
mobile completion for issue #46, because route-specific tables/actions still
need separate sweeps after the active route PRs settle.

## Implemented Change

- Derive compact Cockpit chrome from either manual iPhone preview mode or a
  viewport below the existing mobile breakpoint.
- Keep iPhone preview frame/scaling tied only to the manual preference.
- Let mobile shell content scroll instead of clipping at the shared shell
  boundary.
- Constrain the shared Cockpit shell wrapper to the viewport so the status bar
  stays visible and route content scrolls inside the shell.

## Safety

- Reporting lane, safe extension mode.
- No backend, data, extraction, retrieval, memory, financial truth, runtime, or
  route contract changes.
- No route-specific files touched.

## Validation Notes

- Task card validation, registry claim, and overlap check passed.
- Focused compact-chrome Vitest passed: 1 file, 3 tests.
- Focused ESLint passed on the touched layout/helper/test files.
- Browser plugin was unavailable, so rendered QA used Playwright.
- Playwright with the canonical isolated backend running passed:
  - mobile 390x844: nonblank app, no framework overlay, no console errors, no
    HTTP 4xx/5xx responses, 844px shell wrapper, status bar in viewport, shell
    content `overflow: auto`.
  - desktop 1440x1000: nonblank app, no framework overlay, no console errors,
    no HTTP 4xx/5xx responses, 1000px shell wrapper, status bar in viewport,
    desktop shell content remains `overflow: hidden`.
  - desktop toggle interaction: "Switch to iPhone Scale" changed to "Switch to
    Desktop Scale" and compact shell overflow switched to `auto`.
- Local Next.js generated `next-env.d.ts` drift was restored before staging.
- Dev server and isolated backend were stopped after validation.

## Remaining Scope

This is a shared-shell first slice for #46. It does not claim every Cockpit
route-specific table, chart, action strip, drawer, or chat panel is fully
mobile-complete.
