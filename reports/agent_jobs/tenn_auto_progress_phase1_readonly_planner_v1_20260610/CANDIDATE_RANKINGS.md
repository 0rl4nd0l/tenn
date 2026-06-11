# Candidate Rankings

## Ranking Rules

Higher rank requires:

- control-plane, repo-hygiene, or evaluation scope
- open GitHub issue with current labels
- no default need for GitHub writes, commits, product/runtime/data mutation, or
  broad validation
- clear Phase 2 task-card dry-run path
- contribution to Tenn production readiness through better autonomous execution

## Top Candidates

| Rank | Issue | Score | Why |
| ---: | --- | ---: | --- |
| 1 | #291 `Build Codex-native auto-progress skill workflow` | 95 | Direct tracker for the loop planner; M0, P1, medium risk, ready, safe-extension, control-plane |
| 2 | #281 `Add lint/type gates for financial-engine_v2 backend and scripts` | 84 | Explicit example in #291; validation maturity helps production readiness; Phase 2 can draft only |
| 3 | #234 `Classify stale extraction contract parity diff-check dirt` | 81 | Control-plane dirt classification with strong report-only path and no product mutation required |
| 4 | #139 `Restore or retire missing .cursor architecture rule files` | 74 | M0 control-plane data-missing cleanup; useful but needs architecture-owner decision |
| 5 | #282 `Improve source preview route formatting and copy states` | 58 | Low risk label, but likely cockpit/backend touching; not ideal for control-plane-only loop proof |
| 6 | #140 `Clean root-owned Python cache directories` | 52 | Useful hygiene, but likely requires owner/filesystem cleanup approval |

## Best Next Candidate

Issue #281 is the best Phase 2 dry-run target. It should not be executed in
Phase 2. The next safe lane is to generate a task-card candidate and approval
manifest for exactly one narrow lint-gate slice, then stop.
