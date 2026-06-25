# Handoff Next Goal Print Only

Status: DONE_WITH_RISK

## Objective

Change the Tenn handoff contract so, after `HANDOFF.md` and `NEXT_GOAL.md` are
written, the current session prints only the short fresh-session goal, the
handoff docs path, and a concise git-dirt summary. The full dirt details stay
in `HANDOFF.md` for the next agent.

## Scope

- Updated `.agents/skills/tenn-handoff/SKILL.md`.
- Updated `docs/dev_flow/templates/HANDOFF.md`.
- Updated `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md`.
- Added task card
  `docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md`.

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-handoff-next-goal-print-only-v1-20260624`
- Branch: `control-plane/handoff-next-goal-print-only-v1-20260624`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Starting HEAD: `61d5c9eeac054422eac5230d382cc4e2b36eec6a`
- Guard decision: pass before edits; later guard sees expected allowlisted
  session dirt
- Registry: no active jobs
- Ledger validation: pass

## Current Git Dirt From This Session

- tracked/unstaged:
  - `.agents/skills/tenn-handoff/SKILL.md`
  - `docs/dev_flow/templates/HANDOFF.md`
  - `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md`
- untracked:
  - `docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md`
- ignored/report artifacts:
  - `reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/`
- disposition: session-created, allowlisted, preserved for review/commit or PR.

## Files Intentionally Not Touched

- Product/runtime/backend/frontend paths.
- Extraction/parser/source-PDF/gold-label paths.
- Host-global Codex or agent skill roots.
- Shared generic `docs/dev_flow/templates/NEXT_GOAL.md`.

## Runtime Functionality Proof

not_applicable. This is a control-plane documentation/skill contract change.
No runtime service, pipeline, extraction, or live output was tested.

## Next Recommended Prompt

```text
Review the control-plane handoff next-goal print-only change in
/home/l4nd0/tenn-handoff-next-goal-print-only-v1-20260624. Confirm that
tenn-handoff now prints only the short fresh-session goal plus HANDOFF.md path
and git-dirt summary, then prepare PR only if the diff and report artifacts
remain within the task card allowlist.
```
