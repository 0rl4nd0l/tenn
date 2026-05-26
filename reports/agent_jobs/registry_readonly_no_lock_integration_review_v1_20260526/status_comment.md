## Status update - left open

This issue remains open.

## Summary
In plain language:
- What the issue is: #80's read-only/no-lock registry fix exists on `safe/registry-readonly-no-lock-list-active-v1-20260525`, but this active baseline still does not expose `list-active --read-only`.
- What it impacts: Issue-resolution and audit automation still cannot rely on the requested read-only registry command in this checkout.
- How it restricts Tenn: Agents must continue using lock-backed `list-active` here and record `DATA_MISSING` for the no-lock mode until integration lands.
- Why it is not fixed yet: This review task did not approve cherry-pick, merge, or code integration.

Reason:
- Active baseline check failed: `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` returns `unrecognized arguments: --read-only`.

Current evidence:
- Branch: `codex/long-running-issue-resolution-batch-v1-20260526`
- HEAD: `<filled in live GitHub comment after report commit>`
- Report: `reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/`

Next safe step:
- Run a separate integration task card for #85 that permits only the exact registry files and report artifacts, then cherry-pick or reimplement the bounded `af69c6fe` behavior with focused registry tests.

Hard boundaries preserved:
- No forbidden surfaces mutated.
