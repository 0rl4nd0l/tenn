# Worktree Matrix

Read-only command:

```text
git worktree list --porcelain
```

Classifier result:

| Bucket | Count | Meaning | Recommended Disposition |
| --- | ---: | --- | --- |
| `DEV_FLOW_CONTROL_PLANE` | 82 | Worktrees likely tied to agents, auto-progress, Codex, repo hygiene, issue closeout, merge gates, or workflow control. | Preserve and review before cleanup. |
| `PRODUCT_RUNTIME_EXTRACTION` | 331 | Product, runtime, Cockpit, query, memory, news, extraction, parser, financial truth, source/provenance work. | Owner-boundary; ignore for dev-flow cleanup unless a separate issue owns it. |
| `PRUNABLE_METADATA` | 5 | Worktree metadata points to missing `/tmp` paths. | Review under explicit cleanup approval only. |
| `UNKNOWN_NEEDS_REVIEW` | 61 | Could not safely classify by path/branch keywords or status timed out. | Preserve and review in a later hygiene packet. |
| Total | 479 | Tenn worktree entries. | No deletion or pruning in this run. |

## Current Checkout

| Field | Value |
| --- | --- |
| Path | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Branch | `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609` |
| HEAD | `661f4a089b1eb9b25b1d2eceb9d659b689e5828e` |
| Status | Normal Git status failed; explicit `GIT_DIR`/`GIT_WORK_TREE` status worked. |
| Dirty files | Pre-existing `.githooks/pre-push` and two `git_hook_install_execution` report files, plus this audit card/report. |
| Classification | `UNKNOWN_NEEDS_OWNER_DECISION` |
| Disposition | Preserve; do not clean or repair in this audit. |

## Notable Dev-Flow Worktrees

| Path | Branch | Dirty | Classification | Disposition |
| --- | --- | --- | --- | --- |
| `/home/l4nd0/tenn-agent-contract-registry-main-v1-20260607` | `safe/agent-contract-registry-main-v1-20260607` | clean | `CORE_KEEP` | Review as registry history. |
| `/home/l4nd0/tenn-auto-progress-issue234-phase3-dry-run-review-20260615` | `control-plane/issue234-diff-check-dirt-classification-v1-20260615` | clean | `MERGE_INTO_NEW_WORKFLOW` | Preserve as auto-progress issue-to-card evidence. |
| `/home/l4nd0/tenn-auto-progress-issue291-planner-v2-20260612` | `control-plane/auto-progress-issue291-planner-v2-20260612` | clean | `MERGE_INTO_NEW_WORKFLOW` | Canonical auto-progress evidence. |
| `/home/l4nd0/tenn-auto-progress-phase1-issue281-pr-v1-20260611` | `control-plane/auto-progress-phase1-issue281-closeout-v1-20260611` | clean | `MERGE_INTO_NEW_WORKFLOW` | Preserve. |
| `/home/l4nd0/tenn-git-hygiene-skill-v1-20260607` | `safe/tenn-git-hygiene-skill-v1-20260607` | clean | `MERGE_INTO_NEW_WORKFLOW` | Historical source for Git guard. |
| `/home/l4nd0/tenn-goal-monitor-stop-loop-fix-v1-20260613` | `control-plane/goal-monitor-stop-loop-fix-v1-20260613` | clean | `CORE_KEEP` | Preserve as Stop-hook loop evidence. |
| `/home/l4nd0/tenn-control-plane-pr-closeout-v1-20260607` | detached at PR #300 merge | dirty:1 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; review separately. |
| `/home/l4nd0/tenn-codex-automations-v1-20260516` | `safe/codex-automated-audit-runners-v1-20260516` | dirty:3 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; likely automation history. |
| `/home/l4nd0/tenn-pr335-merge-gate-v1-20260609` | `safe/pr335-merge-gate-v1-20260609` | dirty:1 | `UNKNOWN_NEEDS_OWNER_DECISION` | Preserve; merge-gate evidence. |

## Prunable Metadata Entries

These are metadata-only findings. No prune was run.

| Path | Branch/State | HEAD | Classification |
| --- | --- | --- | --- |
| `/tmp/tenn-appendix4d4e-contract-audit` | `audit/appendix4d4e-contract-expansion-v1` | `5bfdc3f4` | `OWNER_BOUNDARY` |
| `/tmp/tenn-merge-parking-review-wrapper-gate-20260604` | detached | `669d0030` | `OWNER_BOUNDARY` |
| `/tmp/tenn-origin-main-news-verify-20260607` | detached | `7443d9f2` | `OWNER_BOUNDARY` |
| `/tmp/tenn-replay-pr-LskTtF` | `codex/extraction-provenance-replay-reports-v1-20260608` | `a4fd1988` | `OWNER_BOUNDARY` |
| `/tmp/tenn-selector-pr-ziyrOK` | `codex/extraction-scale-table-selector-v1-20260608` | `55ef1fa1` | `OWNER_BOUNDARY` |

## Policy

Native Git Hygiene should not try to make this fleet clean automatically. It
should classify, preserve, and recommend. Cleanup requires a separate exact
approval manifest.
