# Handoff Next Goal

Use this template only when `tenn-handoff` emits a fresh-session continuation
prompt. Non-handoff producers should use `docs/dev_flow/templates/NEXT_GOAL.md`.
After writing this file, the current session should print only the short goal
below, the `HANDOFF.md` path, and a one-line git-dirt summary. The full handoff
stays in `HANDOFF.md`.

## Recommended Prompt

```text
Read <HANDOFF.md path> first, including its Git status and dirt section. Then
run Tenn control-plane preflight (`tenn-git-guard`, task-card validation,
task-ledger validation, active registry read-only check, duplicate-work search,
and a fresh `git status --short --untracked-files=all`). Continue as the
orchestrator only for the work named in the handoff: deal with the recorded
leftover dirt exactly as instructed, preserve the real objective and
do-not-touch boundaries, split only independent lanes, delegate bounded workers
only when useful, review worker outputs before integration, integrate one
coherent change at a time, validate, and report honestly. Stop with
WAITING_ON_USER or DATA_MISSING if the handoff boundary or git-dirt disposition
cannot be safely crossed.
```

## Why This Is Next

- <short evidence-based reason from HANDOFF.md>

## Required Inputs Or Approvals

- <None, DATA_MISSING, or exact approval>

## Final Chat Output

```text
Handoff: <HANDOFF.md path>
Git dirt left behind:
<clean|short tracked/untracked/ignored summary; details in HANDOFF.md>

<paste the Recommended Prompt text above only>
```
