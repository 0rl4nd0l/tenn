---
name: tenn-goal-report
description: Use for Tenn /goal work that needs a visible state machine, report or handoff under reports/agent_jobs, validation tracking, blocked/approval state capture, raw-log pointers, and a next recommended prompt.
---

# Tenn Goal Report

Use this skill for `/goal` runs, long-running repo tasks, blocked handoffs, and
closeout reports.

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
