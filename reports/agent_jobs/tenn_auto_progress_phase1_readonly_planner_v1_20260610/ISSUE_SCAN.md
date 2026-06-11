# Issue Scan

## Controlling Issue

Issue #291: `[Control Plane] Build Codex-native auto-progress skill workflow`

- URL: https://github.com/0rl4nd0l/tenn/issues/291
- State: OPEN
- Milestone: M0 - Control Plane Hardening
- Labels: `lane:evaluation`, `lane:repo-hygiene`, `mode:safe-extension`,
  `priority:p1`, `risk:medium`, `state:ready`, `type:automation`,
  `type:control-plane`
- Phase 1 requested by issue: skill docs, read-only issue/milestone triage,
  compact context packs, ranked candidate matrix, no code mutation.
- Later phases in issue body: issue-to-card dry run, then one safe issue
  execution after gates.

## Bounded Open-Issue Evidence

Read-only label scans found these relevant candidates:

| Issue | Title | Labels Seen | Planner Classification |
| --- | --- | --- | --- |
| #291 | `[Control Plane] Build Codex-native auto-progress skill workflow` | M0, P1, medium, ready, automation, control-plane | Current Phase 1 surface and Phase 2 controller |
| #281 | `[Evaluation] Add lint/type gates for financial-engine_v2 backend and scripts` | P2, medium, ready, validation-gap, evaluation, repo-hygiene | Best Phase 2 dry-run target; execution would need a narrower task card |
| #234 | `[Repo Hygiene] Classify stale extraction contract parity diff-check dirt` | M0, audit, P2, medium, ready, control-plane, validation-gap | Strong report-only or classification candidate |
| #139 | `[Repo Hygiene] Restore or retire missing .cursor architecture rule files` | M0, audit, P1, medium, data-missing, control-plane, docs | Useful M0 control-plane data-missing candidate |
| #282 | `[Cockpit] Improve source preview route formatting and copy states` | P3, low, ready, docs/usability | Lower-risk looking, but touches cockpit/backend area; needs product-boundary check |
| #140 | `[Repo Hygiene] Clean root-owned Python cache directories` | M0, P1, medium, ready, repo-hygiene | Likely blocked on owner/filesystem cleanup approval |

## Notes

- The broad `state:ready` scan was byte-capped and visually large, so only
  candidates material to this Phase 1 report were classified.
- The bounded keyword search for `auto-progress OR Codex-native OR task-card OR
  registry OR worktree OR agent markdown OR Dev Handbook` returned no additional
  JSON rows in this run; label scans were more useful.
- Issue bodies were read for #291, #281, #234, and #139.
