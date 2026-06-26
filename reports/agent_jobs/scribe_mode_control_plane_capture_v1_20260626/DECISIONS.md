# Decisions

## Owner Decisions

- 2026-06-26 16:43 +1000 - Implement Scribe as a control-plane mode inside
  existing Tenn surfaces, not as a new visible skill. - Impact: update
  `tenn-goal-report`, `tenn-fix`, templates, and routing docs only. - Evidence:
  user `/goal` and handoff.
- 2026-06-26 16:43 +1000 - Stop at local commit readiness; do not push, open a
  PR, or merge without approval. - Impact: no GitHub writes. - Evidence: user
  `/goal`.
- 2026-06-26 16:59 +1000 - Proceed with push and draft PR creation. - Impact:
  task card now permits pushing `safe/scribe-mode-control-plane-v1-20260626`
  and opening a draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
  - Evidence: user said "proceed" after draft PR recommendation.
- 2026-06-26 17:01 +1000 - Proceed with the missing-hook-tool push bypass. -
  Impact: rerun push with `TENN_ALLOW_MISSING_HOOK_TOOLS=1` after the hook
  reported missing repo-venv `ruff` and `pytest`. - Evidence: user said
  "proceerd" after the `WAITING_ON_USER` bypass prompt.

## Agent Decisions

- 2026-06-26 16:43 +1000 - Create a fresh sibling worktree from
  `origin/migration/clean-runtime-baseline-reconstruct-v1` instead of using
  `/home/l4nd0/tenn`. - Evidence: handoff classified `/home/l4nd0/tenn` as a
  stale extraction checkout; remote canonical was `857e76c3`. - Risk: local
  branch/worktree creation only.
- 2026-06-26 16:45 +1000 - Keep Scribe in `OPERATOR_NOTES.md`,
  `DECISIONS.md`, and `STATE.md` instead of adding `SCRIBE.md`. - Evidence:
  handoff recommendation and current `SKILLS_SURFACE.md` mode-first policy. -
  Risk: Scribe may remain too implicit if future runs ignore the templates.
- 2026-06-26 16:45 +1000 - Skip live ledger append and write report-local
  intended ledger entries. - Evidence: task card allows ledger validate/search
  only and forbids live ledger mutation. - Risk: live duplicate-work ledger does
  not record this local claim.
- 2026-06-26 16:59 +1000 - Amend the local commit before push so task card and
  report evidence match the owner-approved GitHub write. - Evidence: current
  user approval superseded the earlier no-GitHub-write stop state. - Risk:
  amended commit SHA replaces the local pre-push commit SHA.
- 2026-06-26 17:01 +1000 - Record the pre-push hook block and owner bypass
  approval before rerunning push. - Evidence: Tenn report-state correctness
  requires documenting stale or failed publish gates before PR creation. - Risk:
  amended commit SHA replaces the local pre-push commit SHA again.

## Reversed Or Superseded Decisions

- Local commit-readiness-only stop state was superseded by explicit owner
  approval to push and open a draft PR.
