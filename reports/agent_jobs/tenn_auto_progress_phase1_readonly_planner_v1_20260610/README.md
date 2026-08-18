# Tenn Auto Progress Phase 1 Read-Only Planner

Status: DONE_WITH_RISK

Phase 1 created the read-only planning surface for `tenn-auto-progress`. The
new skill skeleton explains how Codex should scan issues and milestones, rank
candidate work, classify autonomy mandates, build compact context packs, draft
task-card packets, and stop before execution.

No GitHub mutation, commit, push, branch/worktree cleanup, product/runtime/data
mutation, service start, or extraction validation occurred.

## Verdict

The control-plane surface is ready for a Phase 2 dry run, but not for unattended
execution. The best next move is to approve a single issue-to-task-card dry run,
with issue #281 as the recommended target because issue #291 explicitly uses it
as the example auto-progress workflow and it is `state:ready`, P2, medium risk,
and validation-focused.

## Integrated

- Created `.agents/skills/tenn-auto-progress/SKILL.md`.
- Created task card
  `docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md`.
- Created this report bundle with issue scan, milestone scan, candidate ranking,
  mandate classification, context packs, draft task-card packet, and Phase 2
  approval manifest.

## Operational

- Read-only GitHub issue and milestone scanning is manually operational.
- Candidate ranking and context-pack creation are operational as report artifacts.
- Task-card drafting is operational as a non-executing report packet.
- The verifier/approval boundary is explicit.

## Not Operational Yet

- There is no executable `scripts/auto_progress.py` runner.
- There is no deterministic scanner output schema checked into source.
- There is no continuous loop operator.
- There is no executor handoff beyond the draft packet.

## Recommended Phase 2 Prompt

```text
/goal Run Tenn auto-progress Phase 2 issue-to-task-card dry run under REPORT_AUTONOMY and ISSUE_291_READONLY_PLANNER only.

Use `tenn-auto-progress` to refresh read-only GitHub evidence for issue #291 and issue #281, then draft a real task-card candidate for #281 as a report artifact only. Do not execute the task card. Do not commit, push, mutate GitHub, start services, run product/runtime/extraction validation, or touch product/runtime/data/extraction files. Produce a Phase 3 approval manifest that either approves one narrow execution lane or records why owner approval is required.
```
