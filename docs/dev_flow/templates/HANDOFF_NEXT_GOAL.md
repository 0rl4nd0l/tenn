# Handoff Next Goal

Use this template only when `tenn-handoff` emits a fresh-session continuation
prompt. Non-handoff producers should use `docs/dev_flow/templates/NEXT_GOAL.md`.

## Recommended Prompt

```text
Read <HANDOFF.md path> first. Then run Tenn control-plane preflight
(`tenn-git-guard`, task-card validation, task-ledger validation, active registry
read-only check, and duplicate-work search). Continue as the orchestrator only
for the work named in the handoff: preserve the real objective and do-not-touch
boundaries, split only independent lanes, delegate bounded workers only when
useful, review worker outputs before integration, integrate one coherent change
at a time, validate, and report honestly. Stop with WAITING_ON_USER or
DATA_MISSING if the handoff boundary cannot be safely crossed.
```

## Why This Is Next

- <short evidence-based reason from HANDOFF.md>

## Required Inputs Or Approvals

- <None, DATA_MISSING, or exact approval>
