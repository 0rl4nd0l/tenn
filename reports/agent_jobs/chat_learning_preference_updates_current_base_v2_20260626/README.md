# Chat Learning Preference Updates Current-Base Fix

Status: LOCAL_FIX_VALIDATED_READY_TO_PUBLISH

Issue: #254

Worktree:
`/home/l4nd0/tenn-issue254-chat-learning-truth-label-current-base-v2-20260626`

Branch: `safe/issue254-chat-learning-truth-label-current-base-v2-20260626`

Base:
`origin/migration/clean-runtime-baseline-reconstruct-v1@4df1afc941d1008ce135513aee101e5d5275028f`

## Summary

The current-base fix truth-labels the chat learning loop as partially active:
quality scoring telemetry is wired, but live `/chat` traffic does not write
`chat_preferences.json` or automatically learn retrieval/router preferences.

The focused regression proves runtime-shaped session records with only
`quality_metrics` do not produce retrieval/router preferences because they lack
the updater grouping fields: `financial_task_type`, `retrieval_params`, and
`router_role`.

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `PR_BODY.md`
- `REVIEW.md`

## Functionality Status

This is a docs/test truth-label fix. No runtime service was started, no live
`/chat` request was executed, and no production data or preference file was
mutated.

Result: PARTIAL until the PR is merged, canonical containment is verified, and
issue #254 is closed from live GitHub evidence.
