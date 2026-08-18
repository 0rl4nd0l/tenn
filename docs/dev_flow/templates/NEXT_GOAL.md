# Next Goal

> V2 only: create this artifact when both the board decision and `RUN_OUTCOME.json`
> permit a new goal. Do not create it for terminal or no-progress outcomes. A
> permitted goal must target a materially different authorized transition.

## Recommended Prompt

```text
<next exact directly executable /goal, /issue, /review-board, /fix, /explain,
or review prompt. Name the source artifact or task card when one exists, name
the first preflight command when needed, and include the exact stop condition.
Do not assume a HANDOFF.md exists unless this NEXT_GOAL belongs to a handoff
flow. Handoff flows should use docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md.>
```

## Why This Is Next
- <short evidence-based reason>

## Authorized Transition
- Current transition: <completed transition>
- Next transition: <materially different authorized transition>

## Required Inputs Or Approvals
- <None, DATA_MISSING, or exact approval>
