# Handoff

## State

- status: <running|waiting_on_user|blocked|ready_for_next_agent|done_with_risk>
- branch:
- HEAD:
- base:
- task_card:
- report_bundle:

## What Changed

- <summary or none>

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

## Validation

- `<command>`: <exit/status>

## Durable Lessons Learned

- <lesson or none>

## Open Risks

- <risk or none>

## Next Action

<exact next step, owner decision, or follow-up prompt>
