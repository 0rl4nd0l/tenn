# Data Missing

## Non-Blocking

| Item | Status | Reason |
| --- | --- | --- |
| Original 2026-06-02 dirty rewrite writer | `DATA_MISSING_NON_BLOCKING` | The closeout does not require historical writer attribution because the stale dirty state is absent from current canonical and PR #411 preserved the classification packet |

## Blocking

None.

## Reopen Condition

If `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`
becomes dirty again on current canonical, create a fresh repo-hygiene issue with
current evidence instead of reopening stale historical attribution work.
