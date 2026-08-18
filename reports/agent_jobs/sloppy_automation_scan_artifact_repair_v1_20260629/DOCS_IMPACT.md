# Docs Impact

- docs_impact: `DOCS_NOT_REQUIRED`
- docs_checked: `AGENTS.md`, `docs/README.md`,
  `docs/dev_flow/CONTROL_PLANE_STATUS.md`,
  `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`,
  `.github/workflows/sloppy-scan.yml`,
  `.github/workflows/sloppy-fix.yml`, `.sloppy.yml`
- docs_changed: `none`
- docs_followup: `none`
- reason: the durable source of truth for this behavior is the workflow/config
  files themselves. Existing control-plane docs discuss host automation timers
  and repo control-plane status, not detailed Sloppy workflow wiring.
