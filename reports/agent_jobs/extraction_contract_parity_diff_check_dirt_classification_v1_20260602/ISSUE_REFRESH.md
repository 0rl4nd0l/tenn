# Issue Refresh

## Issue #234

- URL: https://github.com/0rl4nd0l/tenn/issues/234
- State: OPEN
- Title: `[Repo Hygiene] Classify stale extraction contract parity diff-check dirt`
- Labels: `mode:audit`, `lane:evaluation`, `lane:repo-hygiene`, `priority:p2`,
  `risk:medium`, `state:ready`, `type:control-plane`,
  `type:validation-gap`
- Milestone: `M0 - Control Plane Hardening`
- Created: 2026-06-02T05:04:19Z
- Updated: 2026-06-02T05:04:19Z
- Comments: none returned by the safe read.

## Issue Claim Refreshed

Issue #234 describes a dirty generated artifact in a shared migration worktree:

`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`

The issue says the dirty version changed from listing the original #98
task-card/code/test/report files to `changed_files: []` while retaining
`ok: true`.

## Related Issue #98

- URL: https://github.com/0rl4nd0l/tenn/issues/98
- State: CLOSED
- Closed: 2026-06-01T17:14:55Z
- Title: `[Financial Truth] Align persisted metric schema with extractor contract`

## Planner Context

The merged V2 auto-progress bundle ranked #234 first with score `85` because it
is open, ready, M0, medium risk, report-first, repo-hygiene/evaluation, and
control-plane.
