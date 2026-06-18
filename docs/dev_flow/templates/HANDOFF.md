# Handoff

## Executive summary

<one-paragraph current state and what the next agent should do>

## State

- status: <running|waiting_on_user|blocked|ready_for_next_agent|done_with_risk>
- branch:
- HEAD:
- base:
- task_card:
- report_bundle:

## Session ID / thread ID / goal ID

- session_id: <id or DATA_MISSING>
- thread_id: <id or DATA_MISSING>
- codex_goal_id: <id or DATA_MISSING>
- source_session_ref: <rollout/log/report pointer or DATA_MISSING>

## Branch/worktree/base

- worktree:
- upstream:
- canonical_head:
- merge_base:
- dirty_state:

## Completed work

- <summary or none>

## What Changed

- <summary or none>

## Commits

- <commit sha and subject, or none>

## PRs

- <PR number, state, checks, mergeability, or none>

## Issues

- <issue refs and state, or none>

## Files changed

- <path>: <change summary>

## Tests and validation

- `<command>`: <exit/status>

## Reports/task cards created

- <path or none>

## Git status and dirt

- <tracked dirt, untracked dirt, ignored generated files, or clean>

## Ledger status

- live_ledger:
- committed_ledger:
- task_id:
- status:
- next_action:

## Docs Impact

- docs_impact: <DOCS_NOT_REQUIRED|DOCS_UPDATED|DOCS_FOLLOWUP|DATA_MISSING>
- docs_checked:
  - <path or none>
- docs_changed:
  - <path or none>
- docs_followup:
  - <issue, task card, report path, or none>
- stale_docs_discovered:
  - <path or none>
- reason: <short reason>

## Model And Subagent Routing

- task_tier: <small|medium|large|critical>
- recommended_model:
- actual_model:
- why_this_model:
- worker_model_allowed:
- worker_decision_limit:
- escalation_needed:
- subagents_used:
  - <worker id, lane, worktree, result file, or none>

## Failed attempts / mistakes

- <attempt and lesson, or none>

## Open risks

- <risk or none>

## Owner decisions needed

- <decision, options, recommended action, or none>

## Durable Lessons Learned

- <lesson or none>

## Next 10 milestones

1. <next milestone>
2. <next milestone>
3. <next milestone>
4. <next milestone>
5. <next milestone>
6. <next milestone>
7. <next milestone>
8. <next milestone>
9. <next milestone>
10. <next milestone>

## Next Action

<exact next step, owner decision, or follow-up prompt>

## Short next `/goal`

<copy-pasteable next goal prompt or none>

## Do-not-touch boundaries

- <boundary or none>

## Evidence grades

- VERIFIED:
- USER_REPORTED:
- INFERRED:
- DATA_MISSING:
