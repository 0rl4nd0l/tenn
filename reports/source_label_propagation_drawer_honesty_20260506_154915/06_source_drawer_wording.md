# Source Drawer / Chat Wording

## Fixed Behavior

The terminal message evidence footer no longer renders:

`Financial facts: source-backed when shown below`

It now renders a role-specific evidence summary:

- `Verified sources`
- `Context sources`
- `Local holdings`
- `Memory context`
- `No relevant source found`
- `Runtime degraded`
- `Evidence incomplete`

## Scope

`sources-drawer.tsx` was validated but not redesigned. The task did not require a new drawer architecture; the visible chat message shell was the place where the misleading generic wording existed.
