# PR Review

## Scope

- Tightens Runtime Functionality Proof closeout exemptions to explicit
  declarations only.
- Adds focused contract and hook regressions for casual `control-plane` and
  negative `report-only` mentions.
- Documents the supported exemption declaration format in the operator guide.

## Safety Review

- Product/runtime/data/extraction/count-24 paths: not touched.
- Greyhound runtime: not touched.
- Host-global files: not touched.
- Visible skills: unchanged; dry-run skill sync still reports `would_link=10`.
- Runtime Functionality Proof: not applicable because this is
  `control_plane_only` validation tooling.

## Decision

Ready for focused PR after final task-card/report validation.
