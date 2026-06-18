---
name: tenn-goal-report
description: Use for Tenn /goal work that needs a visible state machine, report or handoff under reports/agent_jobs, validation tracking, blocked/approval state capture, raw-log pointers, and a next recommended prompt.
---

# Tenn Goal Report

Use this skill for `/goal` runs, long-running repo tasks, blocked handoffs, and
closeout reports.

For long `/goal` runs that need stable judgment before execution, use optional
frame mode by copying the shapes in `docs/dev_flow/templates/FRAME.md`,
`STATE.md`, and `OPERATOR_NOTES.md` into the same report directory. Keep this
mode for long, risky, or multi-turn work; narrow tasks only need the normal
report.

For long `/goal` runs with many files, mixed-risk dirt, cleanup/remediation, or
work that would otherwise create many small approval loops, prefer two-shot mode:
Shot 1 produces the report-local evidence, approval manifest, and Shot 2 plan;
Shot 2 executes approved groups mechanically and closes out.

## State Machine

Maintain one visible state:

- `RUNNING`: safe planned work is in progress.
- `WAITING_ON_USER`: user input or approval is required for the next meaningful
  step.
- `BLOCKED_EXTERNAL`: external service, auth, runtime, filesystem, or data is
  unavailable.
- `VALIDATING`: implementation is complete and checks are running.
- `DONE_WITH_RISK`: useful work completed, but residual risk or unverified
  evidence remains.
- `DONE`: done criteria, validation, and reporting are complete.

## Report Location

Create or update:

```text
reports/agent_jobs/<goal_or_job_id>/README.md
```

If the task card provides `output_dir`, use that directory.

## Optional Frame Mode

Frame mode replaces the old `tenn-frame-design` skill entrypoint. Use it only
when the task needs durable judgment before implementation starts.

Required frame-mode artifacts:

- `FRAME.md`: objective, non-negotiables, scope, evidence, success shape, stop
  states, and steering log.
- `STATE.md`: current state, completed work, blockers, next safe action, and
  validation.
- `OPERATOR_NOTES.md`: concise user steering, corrections, preferences, and
  decisions.

## Required Report Contents

- Objective
- Current state
- Constraints and unsafe actions
- Evidence used
- Files touched
- Files intentionally not touched
- Commands run with exit status
- Approvals needed
- Blocked items and `DATA_MISSING`
- Validation status
- Raw-log paths, if any command output was summarized
- Unsafe actions avoided
- Ignored or untracked artifact note
- Remaining risk
- Next recommended prompt
- Links to Frame artifacts, if used

## Waiting Protocol

When waiting on approval or an external condition, write this block in the report
or handoff before stopping:

```text
WAITING_ON_USER
Needed: <exact approval/flag/input>
Why: <what this unlocks>
Current safe state: <what has been done>
Options: <A/B/C>
Recommended: <one option>
```

If approval is optional, continue only with clearly labeled safe read-only work.
If approval is required for the next meaningful step, stop.
