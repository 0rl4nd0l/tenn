# Worker Result

This is the durable worker contract. It replaces the visible `tenn-worker`
skill entrypoint.

## Assignment
- Branch:
- Worktree:
- Lane:
- Task card:
- Parent task ID:
- Worker ID:
- Result path:
- Stop condition:

## Stop Condition
stop_condition: <copied from WORKER_TASK.md>
stop_condition_hit: <yes|no|DATA_MISSING>
stop_condition_impact: <explanation and impact if hit, otherwise none>

`stop_condition_hit` accepts exactly `yes`, `no`, or `DATA_MISSING`. Do not use
ambiguous values such as `maybe`, `unknown`, or `n/a`.

## Model Routing
- task_tier: <small|medium|large|critical>
- recommended_model: <mini/low-cost|standard coding model|high reasoning|high reasoning plus review-board>
- actual_model: <model tier used or DATA_MISSING>
- why_this_model: <short reason>
- worker_model_allowed: <mini/low-cost|standard coding model|high reasoning|not_applicable>
- worker_decision_limit: <evidence_only|recommendation_only|bounded_implementation|not_applicable>
- escalation_needed: <yes|no>

## Ledger
- Status:
- Touched files:
- Ledger entry written or DATA_MISSING:
- Parent task ID:

## Files Changed
- <path or None>

## Tests Or Checks Run
- `<command>`: <exit/status>

## Risks
- <risk or None>

## Blockers And DATA_MISSING
- <blocker or None>

## Orchestrator Review
- Status: <accepted|revise|park|discard|owner_decision_needed|pending>
- Reason:
- Integrated commit or diff: <sha/path/not_applicable>

## Recommended Action
<integrate|revise|park|discard|ask_owner>
