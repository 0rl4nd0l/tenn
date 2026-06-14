# Gap Analysis

## Answers To The Ten Questions

1. Does a goal monitor actually exist as code, or only as policy?

Both. Host-local `codex-goal-monitor` exists as code. Tenn repo `tenn-goal-report` and `tenn-frame-design` are policy/reporting skills, not an enforcing monitor.

2. Does `/goal` state get written anywhere durable?

Yes. Current evidence shows `~/.codex/goals_1.sqlite` with `thread_goals` status values including `active`, `blocked`, and `complete`.

3. What marks a goal terminal?

In the Codex DB, `complete` is terminal. In Tenn reports, `DONE`, `DONE_WITH_RISK`, `WAITING_ON_USER`, and `BLOCKED_EXTERNAL` are terminal or stop states. Handoff paths are terminal only by instruction, not by code.

4. Does the stop hook enforce terminal state or merely warn?

Repo Stop hook enforces task-card contract failures, not terminal goal state. Host Stop hook merely warns about dirty state.

5. Why did the session continue after saying "close here"?

No inspected code recognizes “handoff complete” as a terminal event. Stop-hook output gave the model more context to answer, so it continued.

6. Is the dirty milestone warning causing repeated loop output?

Likely yes. Current host `stop_check.py` repeats `MILESTONE NOT COMMITTED` while dirty files remain and has no de-duplication.

7. Is there a "no more work after handoff" rule?

Only in handoff text and skill policy. No code-level rule was found.

8. Is there a repeated-response detector?

No repeated-response detector was found in repo hook code or host goal optimizer code inspected.

9. Is there a token-burn guard?

Yes, host-local `goal_optimizer_pre_tool.py` and `codex-goal-monitor` warn on high-burn commands and goal burn thresholds. They are warning-first and read-only.

10. What minimal fix would prevent this exact failure?

Two layers are needed:

- Repo-side immediate fix: successful Codex Stop contract checks should be silent. Implemented here.
- Host-global follow-up: `stop_check.py` should de-duplicate dirty warnings, use the active cwd instead of hard-coded `/home/l4nd0/tenn`, classify warnings as informational, and suppress dirty warnings when a handoff-complete terminal marker is present.

## Residual Risk

The repo-side fix reduces one Stop-hook loop source. It does not modify host-global `~/.codex/hooks/stop_check.py`, which remains the likely source of the repeated dirty milestone warning.
