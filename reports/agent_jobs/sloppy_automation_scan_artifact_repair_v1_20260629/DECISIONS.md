# Decisions

## Decisions Made

- Used a sibling task worktree because `/home/l4nd0/tenn` had unrelated
  `AGENTS.md` dirt.
- Kept the repair to the Sloppy workflow/config surface instead of changing
  host systemd timers, Codex hooks, secrets, or runtime state.
- Set the Sloppy scan artifact path in both `.sloppy.yml` and
  `.github/workflows/sloppy-scan.yml` so the action has an explicit value even
  if one config source is ignored.
- Aligned Sloppy Fix with the default-branch Claude workflow-run behavior
  instead of preserving the stale scheduled Codex workflow.
- Closed as `DONE_WITH_RISK` because live GitHub automation functionality was
  not proven without a push/run.

## Decisions Not Made

- Did not decide whether to dispatch Sloppy manually.
- Did not decide whether to push or open a PR.
- Did not decide whether host-local `memory-drift` should be rerun or modified.
