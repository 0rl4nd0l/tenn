# Next Goal

## Recommended Prompt

```text
Read reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/handoff/HANDOFF.md first. Then run Tenn control-plane preflight (`tenn-git-guard`, task-card validation, task-ledger validation, active registry read-only check, and duplicate-work search). Continue as the orchestrator: preserve the real objective and do-not-touch boundaries, review validation and PR state, split only independent lanes, delegate bounded workers only when useful, review worker outputs before integration, integrate one coherent change at a time, validate, and report honestly. Stop with WAITING_ON_USER or DATA_MISSING if a boundary cannot be safely crossed.
```

## Why This Is Next

- The local control-plane diff is designed for a focused PR and has report-local
  evidence.

## Required Inputs Or Approvals

- None beyond the already requested focused PR flow.
