# Review

## Findings

No blocking findings in the #249 diff.

## Review Evidence

- The helper extraction keeps `app.api.routes.require_api_key` available as the
  same imported function for existing route modules and tests.
- `chat.py` now depends on lightweight `app.api.auth`, avoiding a broad
  `app.api.routes` import from the legacy chat module.
- Tests cover both mounts and both side-effect families:
  analysis (`chat_with_tenn`, `record_turn`) and strategy (`propose_change`,
  `confirm_change`, `apply_change`).
- Matching-key tests preserve analysis behavior for both legacy mounts.
- `check-diff` reports no disallowed files.

## Residual Risk

No live backend service was started. Full `test_local_api_key.py` did not pass
in the lightweight local dependency environment because optional Cockpit route
modules were absent from `main.app`; CI or a full backend environment should
provide the broader route-registry proof.
