# Tenn Auto Progress Issue 291 Read-Only Planner V2

Status: PR_PRESERVATION_APPROVED

This slice makes `tenn-auto-progress` reusable for deterministic read-only
issue/milestone triage and issue-to-task-card dry runs.

## Implemented

- Added `scripts/auto_progress.py`.
- Refined `.agents/skills/tenn-auto-progress/SKILL.md` with script usage.
- Created a v2 task card for this control-plane slice.
- Generated compact report artifacts from read-only GitHub evidence.
- Drafted a report-only task-card packet for top candidate issue #234.

## Current Top Candidate

Top candidate after ranking: issue #234,
`[Repo Hygiene] Classify stale extraction contract parity diff-check dirt`.

Why: open, ready, M0, control-plane, audit mode, repo-hygiene/evaluation lanes,
medium risk, and report-first. The script demotes #140 because it is a
root-owned/filesystem cleanup boundary.

## Stop Boundary

No candidate execution occurred. No real #234 task card was created. The later
preservation approval only permits committing these V2 control-plane artifacts,
pushing this branch, and opening a PR. It does not permit #234 execution,
product/runtime/data/extraction mutation, service starts, broad validation, or
any GitHub mutation beyond opening the preservation PR.

## Preservation Check

On 2026-06-13, the branch was revalidated from the sibling worktree. Current
target `origin/migration/clean-runtime-baseline-reconstruct-v1` had advanced,
but the intervening target changes did not overlap these V2 control-plane paths.
The required `triage_check` and `issue234_check` dry-run artifacts were generated
under this report bundle.

## Next Prompt

```text
/goal Run Tenn auto-progress Phase 3 dry-run review for issue #234 under REPORT_AUTONOMY only.

Use reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/DRAFT_TASK_CARD_ISSUE_234.md as the draft packet. Create the real report-only task card only if the allowlist is still exact, refresh issue #234 and registry read-only evidence, classify the stale diff-check artifact, and stop before artifact restoration, GitHub mutation, commits, product/runtime/data/extraction mutation, cleanup, stash, reset, merge, rebase, cherry-pick, branch deletion, or worktree removal.
```
