# PR #39 / Issue #105 Audit Preservation Review

## Summary

The completed issue #105 audit bundle is present, parseable, and acceptable as
audit evidence. It is not yet durable in git: the prior task card is untracked
and the prior report directory is ignored/untracked. PR #39 is still open,
draft, unmerged, and red on the same GitHub CI evidence inspected by the prior
audit.

This review did not edit the prior PR39 audit artifacts, product/runtime/test
files, dependencies, workflows, GitHub state, or production data.

## Current Checkout

| Item | Result |
| --- | --- |
| Worktree path | `/home/l4nd0/tenn-runtime` |
| Worktree realpath | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| HEAD | `810c2b0ef60ed205e15f9d4dd2eb16773e69f98a` |
| Canonical Tenn checkout | yes, this is the active Tenn runtime checkout realpath |
| Recent top commit | `810c2b0e milestone(news): standardize news artifact paths` |
| Registry active jobs | none at read-only preflight |
| Registry claim | not attempted; check-overlap failed on dirty files outside this task allowlist |

The local branch is ahead of PR #39's current GitHub head. This review treats
GitHub PR #39 state as authoritative for PR readiness.

## Prior #105 Artifact Inventory

| Artifact | Status | Git state |
| --- | --- | --- |
| `docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md` | present | untracked, not committed |
| `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/` | present | ignored, not committed |
| `README.md` | present | under ignored report dir |
| `status.json` | present, JSON parse passed | under ignored report dir |
| `failure_clusters.json` | present, JSON parse passed | under ignored report dir |
| `diff-check.json` | present, JSON parse passed | under ignored report dir |
| `child_task_proposals.md` | present | under ignored report dir |
| `pr39_merge_readiness.md` | present | under ignored report dir |

The prior report records 13 failure clusters, `root_cause_fixed: false`,
`follow_up_required: true`, and Project Memory save recommendation
`RECOMMENDED`.

## Current PR And Issue State

| Item | Result |
| --- | --- |
| Issue #105 | open: `[CI] Split PR #39 lint-and-test failure clusters after closed CI audit` |
| PR #39 | open, draft, unmerged |
| Head | `8635833b7d7359ed55daf0495eb49c5457bab91d` |
| Base | `36130cbdb98e7084e8396d125a1d6f8d3ab48bc7` |
| Shape | 38 commits, 346 changed files, 39,618 additions, 190 deletions |
| Merge state | `UNSTABLE`; mergeable reports true |
| Checks | `lint-and-test` failed, `scan` passed |
| Latest failed run | `26439822448`, job `77831209696` |
| Latest passed scan run | `26439822445`, job `77831209694` |

This matches the prior audit's PR/CI evidence. Older run `26379324415` remains
superseded by run `26439822448`.

## Validation Results

| Check | Result |
| --- | --- |
| New task-card validate | passed |
| Registry list-active read-only | passed, no active jobs |
| Registry check-overlap | failed because dirty files existed outside this task allowlist |
| Registry claim/release | not attempted / not needed |
| Prior `status.json` parse | passed |
| Prior `failure_clusters.json` parse | passed |
| Prior `diff-check.json` parse | passed |
| GitHub PR/issue/check inspection | passed read-only |
| Generated JSON parse | passed |
| `git diff --check` | passed |
| New task-card `check-diff` | failed: prior issue #105 task card is untracked outside this task allowlist |
| GitHub mutation | none |
| Production data access | false |

The task-card validator does not currently include `Repo Hygiene` in its formal
lane enum. This card therefore uses validator lane `Reporting` and records the
requested primary lane as `Repo Hygiene`.

## Dirty Work Classification

Current default status after the inspection settled shows only:

- `docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md`
  as this job's allowed untracked task card.
- `docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
  as the prior PR39 audit task card, untracked and outside this job's allowlist.

During preflight and registry overlap, transient unrelated files were also
observed in Cockpit core and news-artifact surfaces, including
`financial-engine_v2/cockpit/core/actions.py`,
`financial-engine_v2/cockpit/core/tools.py`,
`financial-engine_v2/backend/app/services/news_health_status.py`,
`financial-engine_v2/shared/news_artifacts.py`, and
`scripts/news_pipeline/cli_common.py`. They were not cleaned, stashed, reset,
deleted, restored, overwritten, or edited by this job.

Full classification is in `dirty_work_matrix.json`.

Final task-card `check-diff` is therefore **PARTIAL_BLOCKED_BY_UNRELATED_DIRTY_WORK**:
this job's own task card is allowed, but
`docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
remains untracked outside this task's allowed files. It was not edited.

## Acceptance Decision

The prior issue #105 audit can be accepted as audit evidence. It should not be
treated as remediation, merge readiness, or issue closeout. The evidence is
reviewable locally and current against GitHub PR/check state, but it is not
durable in git until a separate approved preservation task commits or parks the
prior task card/report.

Issue #105 should stay open. It needs child remediation or explicit parking
decisions for the 13 clusters before closure. Closed issue #66 remains only the
precursor audit, and closed issue #55 remains remediated/out of queue.

PR #39 should remain draft and **NOT_MERGE_READY / PARKING_RECOMMENDED**.

## Recommended Child Task Order

1. C01 - Reconcile backend sqlite3/uuid4/vector architecture invariants.
2. C02 - Align Cockpit chat/session `llm_client` contract drift.
3. C03 - Make Cockpit subagent event-loop contract explicit.
4. C04 - Align streaming subprocess helper tests with required `job_id`.
5. C05 - Verify or carry the Ollama URL loader repair into PR #39.
6. C08 - Decide HybridRouter force-local and stream callback contract.
7. C07 - Reconcile Cockpit stress expectations with grounded refusals.
8. C09 - Restore or re-contract memo extractor signal routing.
9. C13 - Restore query sufficiency guard for missing financial rows.
10. C11 - Resolve missing real-gold 10X PDF asset provenance/path.
11. C12 - Isolate process-document API from live Redis/Celery or declare CI service.
12. C06 - Stabilize marketplace wall-clock-sensitive fixture expectations.
13. C10 - Settle Cockpit preferences `chat_runtime_target` API contract.

## Save Recommendation

Project Memory save is **RECOMMENDED** after operator review because the prior
cluster map plus this preservation review should guide several follow-up tasks.
No memory write was performed by this audit-only job.
