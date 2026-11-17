# Cockpit Accessible Form Controls Audit

## Summary

This report is an audit-only closeout for issue #53. It creates a current
route-by-route inventory of visible Cockpit form controls and button-like
controls with missing programmatic names.

No product source files were changed.

## Current Evidence

- GitHub issue checked: #53, open, Reporting/Cockpit audit-first scope.
- Duplicate/overlap search: no matching accessible-controls PR was found.
- Open adjacent PR files were inspected; the next implementation slice should
  avoid Marketplace, History, Verification source, Home narrative, Boot,
  Watchlist, Operations, and Thesis Audit files currently owned by open PRs.
- Rendered audit: Playwright Chromium against `http://127.0.0.1:3013`.
- API routes were mocked with empty `DATA_MISSING`-shaped responses to avoid
  production data access and capture empty/error-state DOM controls.
- Inventory: 15 routes, 223 visible controls, 52 failures.

## Artifacts

- `accessibility_inventory.json`: full route/control/failure inventory.
- `findings.md`: issue clusters, source anchors, and next safe remediation
  slices.
- `validation.json`: task-card validation.
- `status.json`: registry claim/release status.
- `diff-check.json`: task-card diff validation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260601.md`
- Playwright Chromium DOM inventory for `/full-chat`, `/holdings`, `/news`,
  `/verification`, `/marketplace`, `/marketplace/alerts`,
  `/marketplace/matches`, `/memory`, `/thesis-audit`, `/updater`,
  `/intel-ops`, `/history`, `/operations`, `/settings`, and `/watchlist`.

## Next Safe Step

Open a focused implementation task for the lowest-collision files:

- `cockpit-ui/components/cockpit/chat/terminal-input.tsx`
- `cockpit-ui/components/cockpit/holdings/holdings-screen.tsx`
- `cockpit-ui/components/cockpit/holdings/holdings-screen.test.tsx`

Do not include Marketplace, History, Thesis Audit, Operations, Verification, or
Watchlist product files in that first implementation slice while adjacent PRs
remain open.
