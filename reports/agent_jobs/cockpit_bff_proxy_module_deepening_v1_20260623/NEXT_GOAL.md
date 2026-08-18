# Next Goal

After this slice lands, continue Cockpit BFF proxy deepening by migrating one
additional route cluster with existing tests.

Recommended next candidates:

- `cockpit-ui/app/api/cockpit/marketplace/missions/**`
- `cockpit-ui/app/api/cockpit/marketplace/matches/**`
- `cockpit-ui/app/api/cockpit/memory/**`

Keep the same rule: one route cluster per PR, focused tests first, no backend or
UI component behavior changes.
