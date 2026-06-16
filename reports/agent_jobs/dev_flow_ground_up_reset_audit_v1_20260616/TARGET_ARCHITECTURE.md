# Target Architecture

## Smallest Future Stack

| Component | Purpose | Invoked By | Inputs | Outputs | Allowed Mutations | Stop States | Git Hygiene Relation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `tenn-issue` | Frame vague problems into executable issues. | Orlando `/issue`. | User problem, repo/GitHub/report evidence. | `ISSUE.md`, `MILESTONES.md`, context pack, `NEXT_GOAL.md`. | Report-local drafts only by default. | `DONE`, `DONE_WITH_RISK`, `WAITING_ON_USER`, `DATA_MISSING`. | Mandatory preflight and candidate ranking. |
| `tenn-review-board` | Independent perspectives and decision. | Orlando before risky decisions. | Issue, PR, branch, report, diff. | `BOARD.md`, `BOARD_DECISION.json`, `NEXT_GOAL.md`. | Report-local. | merge/fix/park/block/supersede. | Must classify branch/PR/dirty state first. |
| `tenn-fix` | Orchestrate implementation. | Orlando `/fix`. | Issue or board decision, task card. | `STATE.md`, validation, PR draft/URL if approved. | Task-card allowlist only. | done, blocked, waiting, validation failed. | Owns worker worktrees and post-run diff. |
| `tenn-worker` | Bounded subagent execution. | `tenn-fix`. | Worker brief, lane, worktree, allowed paths. | `WORKER_RESULT.md`. | Only assigned scope. | completed, blocked, data-missing. | One worker, one worktree, no unreported dirt. |
| `tenn-explain` | Layman-depth explanation. | Orlando `/explain`. | Issue, PR, branch, report, subsystem, skill. | `EXPLAIN.md` when durable. | Report-local only. | done or data-missing. | Runs read-only Git guard for branch/PR topics. |
| `tenn-code-reviewer` | Final diff/PR review. | `tenn-fix`, Orlando. | Diff, task card, validation logs. | `PR_REVIEW.md`. | Read-only by default. | pass/fail/block. | Refuses review if diff scope unknown. |
| `tenn-improve-codebase-architecture` | Find or execute structural improvements. | Orlando. | Domain docs, code map, issue/board decision. | Architecture report, bounded task card. | Report-only unless execution mode approved. | recommendation, waiting, fixed, blocked. | Must use task-card and Git guard for execution. |
| `tenn-git-guard` | Quiet backend safety guard. | Every command. | Worktree, branch, dirty files, PRs, registry. | preflight JSON/markdown, dirty classification. | None by default. | pass, warning, block, data-missing. | The Git Hygiene backend. |

## Minimum Artifact Set

| Artifact | Keep? | Role |
| --- | --- | --- |
| `ISSUE.md` | Yes | Problem framing and current evidence. |
| `MILESTONES.md` | Yes | Phased route from issue to completion. |
| `BOARD.md` | Yes | Multi-perspective review narrative. |
| `BOARD_DECISION.json` | Yes | Machine-readable decision. |
| `NEXT_GOAL.md` | Yes | Concrete next command/prompt. |
| `STATE.md` | Yes | Current orchestrator state. |
| `WORKER_RESULT.md` | Yes | Worker closeout. |
| `PR_REVIEW.md` | Yes | Final code review. |
| `DECISIONS.md` | Yes | Durable owner/agent decisions. |
| `EXPLAIN.md` | Yes | Durable explanation. |

## Product/Runtime/Extraction Boundary

All target components default to no product/runtime/data/extraction mutation.
Execution mode requires a task card, exact allowlist, owner approval when
crossing high-risk boundaries, and focused validation.
