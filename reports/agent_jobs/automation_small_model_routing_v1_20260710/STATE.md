# Automation Small Model Routing V1 State

Status: DONE_WITH_RISK

## Current Evidence

- Task worktree:
  `/home/l4nd0/tenn-automation-small-model-routing-v1-20260710`
- Branch: `control-plane/automation-small-model-routing-v1-20260710`
- Base HEAD: `ed481f4a333d3d62e944ccd48a6fcdccbfb67068`
- Tenn guard: pass before task-card creation.
- Focused unit tests: 13 tests passed.
- Dry-run proof:
  - `repo-hygiene` command includes `--model gpt-5.4-mini` and
    `model_reasoning_effort="medium"`.
  - `extraction-regression` command has no explicit model override and keeps
    the configured Codex default.

## Boundaries

- Repo-side runner, tests, docs, and report artifacts only.
- No live timer/service/runtime/data mutation.
- No GitHub mutation.

## Runtime / Rollout Caveat

This change is proven in the task worktree by command-construction tests and
dry-run output. It does not mutate the installed user timers or the automation
execution worktree. Live scheduled automations will use the new routing only
after this branch is merged and the execution surface is updated to that
content.

## Next Step

Review and merge this control-plane change, then update the automation
execution surface if live timer behavior should change immediately.
