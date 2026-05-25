# Cockpit Home Strategy Lab Declutter v1

## Status

- Branch: `safe/cockpit-home-strategy-lab-declutter-v1-20260525`
- Base HEAD: `f2ee3aa1c393`
- Lane: Reporting
- Execution mode: SAFE EXTENSION
- Collision risk: MEDIUM
- Registry claim: `cockpit_home_strategy_lab_declutter_v1_20260525`

## Before/After UX

Before: Cockpit Home rendered Strategy Lab / QuantDinger with verbose evidence by default: repeated safety pills, full evidence artifact paths, smoke internals, review queue rows, export packet paths, and long DATA_MISSING detail.

After: Cockpit Home renders a compact Strategy Lab summary plus a collapsed artifact-review drilldown. Detailed evidence remains reachable through `View details`, `Open Strategy Lab`, and the expanded artifact review card.

## Exact Home Wording

- Status: `Read-only sandbox proof verified`
- Current runtime: `Offline`
- Review state: `Pending review`
- Trading/execution: `Disabled`
- Value: `Repo-backed proof exists for read-only sandbox behavior; QD is not live or executable.`
- Blocker: `DATA_MISSING: No current QuantDinger sidecar capability, auth, network transport, retry, timeout, or unavailable behavior is confirmed by this status route.`
- Affordances: `View details`, `Open Strategy Lab`

## Details Moved

Hidden from default Home:

- full artifact path lists
- individual payload refs
- fixture rows
- export packet lists
- repeated no-trading/no-store-write labels
- historical smoke internals
- review queue rows
- long DATA_MISSING lists

Still available in details:

- Strategy Lab artifact review route: `/api/cockpit/strategy-lab/artifacts`
- Strategy Lab status route: `/api/cockpit/strategy-lab/status`
- expanded artifact review card after clicking `View details`
- review queue rows, experiment session envelope, export packets, artifact source paths, and DATA_MISSING detail

## Validation

- Task card validate: PASS
- Registry check-overlap: PASS
- Registry claim: PASS
- Focused Vitest: PASS, 5 files and 11 tests
- TypeScript: PASS
- Targeted ESLint: PASS
- Forbidden promotion grep: PASS, no `current_sidecar_available: true`, `execution_allowed: true`, `canonical_financial_truth: true`, live trading, paper trading, or paper order promotion found in touched Strategy Lab files
- `git diff --check`: PASS
- Rendered smoke: PASS with Playwright fallback because Browser plugin is absent

## Rendered Smoke

- Desktop URL: `http://127.0.0.1:3215/`
- Desktop viewport: `1440x900`
- Mobile viewport: `390x844`
- Screenshot evidence:
  - `/tmp/cockpit-home-strategy-lab-declutter-1440.png`
  - `/tmp/cockpit-home-strategy-lab-declutter-mobile.png`
- Checks: page identity, nonblank content, no framework overlay, no console errors, compact status visible, review rows hidden by default, artifact path hidden by default, drilldown button visible, details visible after click.

## Remaining UX Gaps

- `View details` currently opens the repo-backed API route and the Home card expands technical details in place. A dedicated analyst-facing Strategy Lab page would be cleaner if this subsystem gets a full UI route later.
- The blocker summary is intentionally conservative and still contains DATA_MISSING because the current sidecar remains offline and not integrated.

## Save Recommendation

Save as a milestone commit after `check-diff` and registry release pass. Do not merge this into a shared dirty checkout until the user chooses the integration branch.
