# Current Goal Monitor Surface

## Summary

There are two different control surfaces:

- Repo-local Tenn Stop hook: `.codex/hooks.json` runs `python3 scripts/agent_job_hook.py --platform codex --event Stop`.
- Host-local goal tooling: `codex-goal`, `codex-goal-monitor`, `codex-goal-preflight`, `codex-goal-handoff`, `codex-capture`, `~/.codex/goal.config.toml`, and `~/.codex/hooks/goal_optimizer_pre_tool.py`.

The repo-local hook is real code, but it is a task-card/registry/diff contract hook. It is not a goal monitor.

The host-local `codex-goal-monitor` is real code and reads `~/.codex/goals_1.sqlite` plus rollout JSONL token events. It is read-only and warning-oriented. It does not enforce terminal state.

## Durable `/goal` State

Current live evidence shows durable slash-goal state in `~/.codex/goals_1.sqlite`.

Observed schema:

```text
thread_goals(
  thread_id TEXT PRIMARY KEY,
  goal_id TEXT,
  objective TEXT,
  status TEXT CHECK(status IN ('active','paused','blocked','usage_limited','budget_limited','complete')),
  token_budget INTEGER,
  tokens_used INTEGER,
  time_used_seconds INTEGER,
  created_at_ms INTEGER,
  updated_at_ms INTEGER
)
```

The repo itself has report-local state conventions in `tenn-goal-report` and `tenn-frame-design`, but those are Markdown policy artifacts unless an agent writes them.

## Terminal State Semantics

Current surfaces disagree:

- Codex durable DB terminal status: `complete`, plus non-active statuses `blocked`, `usage_limited`, `budget_limited`, and `paused`.
- Tenn report policy terminal/report states: `DONE`, `DONE_WITH_RISK`, `WAITING_ON_USER`, `BLOCKED_EXTERNAL`.
- Handoff files: terminal only by instruction text, not enforced by code.
- Repo Stop hook: terminal is not modeled; it only blocks or allows based on task-card contract checks.

## Current Goal Monitor Run

`codex-goal-monitor --current` exited 0 and reported this active goal as `CONTINUE`, with actual rollout tokens below policy thresholds. This proves the monitor can warn on burn, but it did not treat this work as terminal and cannot enforce a stop.

## DATA_MISSING

- Exact raw transcript after `/tmp/greyhound_accuracy_odds_closeout_20260613T0854.md` was created is not available from the provided artifact set.
- Whether the original looping session had an active Tenn task card is `DATA_MISSING`.
