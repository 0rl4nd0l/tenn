# Normalize Jam-Captured GitHub Issues

Generated: 2026-05-27T13:49:32+10:00

## Summary

Issue #106 is complete and closed. The five raw or under-specified target issues
were either normalized in place or explicitly classified with `DATA_MISSING` and
linked to adjacent trackers.

No product/backend/frontend/runtime code, DB, Qdrant, news store, memory store,
canonical financial truth, parser route, extraction prompt, gold label,
model/runtime/GPU/service config, branch, PR, or unrelated issue was mutated.

## Preflight

- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Starting HEAD: `60db8e068f6c8f6d30ed4cbaaac1f9c8260379f9`
- HEAD moved during this run to `82e62c3f86c395d69190a511eacb92648081ed73`
  via `milestone(evaluation): integrate extraction eval foundation`.
- Remote: `origin https://github.com/0rl4nd0l/tenn.git`
- Initial git status: clean.
- Registry before claim: no active jobs.
- Registry claim: created for `normalize_jam_captured_github_issues_v1_20260526`.
- Registry after HEAD moved: another active Query Orchestration job appeared in
  `/home/l4nd0/tenn-extraction-terminal-state-live-candidate-export-v1-20260527`;
  it owns extraction-terminal-state report files only and does not overlap this
  task/report bundle.

## Target Outcomes

| Issue | Outcome | Labels/Milestone |
| --- | --- | --- |
| #40 `failure to request a search` | `DATA_MISSING`, linked to adjacent #83/#104/#107/#116 | M3; query/reporting/provenance audit labels |
| #41 `missing data` | `DATA_MISSING`, linked to #86/#116/#83/#114 | M5; reporting/cockpit audit labels |
| #53 `Production Cockpit forms rely on placeholders and unlabeled icon controls` | normalized in place | M5; reporting/cockpit usability/validation-gap labels |
| #55 `Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound` | normalized in place | M6; runtime/reporting security/control-plane labels |
| #61 `Cockpit should default visible GPU to the llama-server GPU` | normalized in place | M6; runtime/reporting bug/usability labels |
| #106 `Normalize raw Jam-captured GitHub issues into Tenn issue contract` | closed after all targets classified | M0; `state:done-remediated` |

## Jam Evidence

- #40 Jam details and screenshot were available. Console-log retrieval returned
  HTTP 404, so the issue remains `DATA_MISSING` rather than implementation-ready.
- #41 Jam details and screenshot were available. No processed console/network
  payloads were available, so the issue remains `DATA_MISSING` with links to
  narrower existing Home/news/runtime trackers.

## Duplicate/Supersession Decisions

- #40: no exact duplicate found; adjacent #83, #104, #107, and #116 are linked.
- #41: no exact duplicate found; the screenshot splits across #86, #116, #83,
  and #114.
- #53: no exact duplicate found.
- #55: #51 is adjacent UI-confirmation coverage, not duplicate server-side guard
  coverage.
- #61: #90 and #113 are related runtime observability issues, not duplicate
  default-visible-GPU coverage.

## GitHub Mutations

- Edited bodies for #40, #41, #53, #55, and #61 only.
- Applied existing labels and milestones to #40, #41, #53, #55, and #61 only.
- Removed generic `bug` from #41 after applying `type:bug`.
- Added one closeout comment to #106.
- Replaced #106 `state:ready` with `state:done-remediated`.
- Closed #106.

## DATA_MISSING

- GitHub Projects fields were not inspected or mutated.
- #40 console/network payloads are missing; Jam console fetch returned HTTP 404.
- #41 console/network payloads are missing; Jam had no processed events.
- Current runtime reproduction for #40/#41 was not run because this pass was
  issue normalization, not product validation.
- Remote durability of this local report commit is not proven by this task.

## Recommended Next

Run a narrower target issue next rather than reopening #106. The highest-risk
normalized issue is #55 because it is a server-side restart-route guard/security
audit. If continuing by backlog priority instead, keep the active registry
surface in view before starting Evaluation or Query Orchestration work.
