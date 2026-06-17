# Model Routing

## Task Tier

- task_tier: <small|medium|large|critical>
- recommended_model: <mini/low-cost|standard coding model|high reasoning|high reasoning plus review-board>
- actual_model: <model tier used or DATA_MISSING>
- why_this_model: <short reason>

## Worker Authority

- worker_model_allowed: <mini/low-cost|standard coding model|high reasoning|not_applicable>
- worker_decision_limit: <evidence_only|recommendation_only|bounded_implementation|not_applicable>
- escalation_needed: <yes|no>

## Tier Guide

- `small`: grep/search, JSON parse, file listing, report summarization, simple
  docs update, focused test run. Use mini/low-cost workers when available.
- `medium`: small bug fix, one/two-file code change, targeted regression, PR
  comment fix. Use a standard coding model.
- `large`: multi-file correctness, schema/persistence, architecture change, or
  tricky debugging. Use a high reasoning model.
- `critical`: DB/runtime mutation, destructive Git, financial truth, merge
  conflict, high-risk cleanup, or owner-boundary decision. Use high reasoning
  plus review board or owner decision.

## Delegation Rules

- Use smaller/cheaper workers for bounded evidence gathering.
- Do not let small models make final decisions on high-risk work.
- Use high reasoning models for architecture, schema, financial truth, merge
  readiness, destructive operations, and owner-boundary decisions.
- For hard tasks, optionally use short read-only strategy bids and record why
  the selected plan won on testability, blast radius, value, and cost.
- Delegate subagents only when lanes are independent and isolated by worktree,
  branch, result file, and task-card allowlist.
