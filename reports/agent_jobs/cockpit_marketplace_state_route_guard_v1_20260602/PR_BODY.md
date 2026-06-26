## Summary

- Require the configured local API key for direct backend Cockpit Marketplace mission, match, feedback, benchmark-review, link/unlink, and alert state routes.
- Add focused backend denial, no-side-effect, authenticated-success, and route-registration coverage.
- Preserve scan, calibration, eBay sync, browser health, scoring, matching, scheduler, runtime, DB, and frontend behavior.

## Validation

- RED on current base with final test-only patch: `43 failed, 35 passed, 5 warnings`
- GREEN: `78 passed, 5 warnings`
- Ruff: passed
- `python3 -m py_compile`: passed
- `git diff --check`: passed
- Task-card validation: passed
- Ledger validation: passed

Runtime functionality proof is `PARTIAL`: local backend tests passed, but no live deployed backend/browser route probe was performed.

Closes #227
