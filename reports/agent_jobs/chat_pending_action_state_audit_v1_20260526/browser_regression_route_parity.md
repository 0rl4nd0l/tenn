# Cockpit Browser Regression Route Parity

Generated: 2026-06-01T16:34:48.291Z
Verification target: http://localhost:3000

| Page/Route | Control/Area | Expected | Observed | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| /full-chat | Pending action follow-up | A normal prompt submitted while Confirm/Cancel is visible completes as an independent chat turn without running the action | Independent plain answer rendered after action proposal; backend action POST count remained 0 | PASS | Regression coverage for issue #120; confirmation gate stayed intact |
