# Model Routing Design

## Goal

Make task difficulty and model cost explicit so small work uses cheap workers,
hard work gets enough reasoning, and final decisions are not delegated to weak
models.

## Task Tiers

| Tier | Examples | Recommended model | Decision authority |
| --- | --- | --- | --- |
| `small` | grep/search, JSON parse, file listing, report summarization, simple docs update, focused test run | mini/low-cost | May gather evidence and make low-risk local recommendations. |
| `medium` | small bug fix, one/two-file code change, targeted regression, PR comment fix | standard coding model | May implement inside task-card allowlist; reviewer still required. |
| `large` | multi-file extraction correctness, schema/persistence, architecture change, tricky debugging | high reasoning model | Orchestrator owns final plan; workers gather/implement bounded lanes. |
| `critical` | DB/runtime mutation, destructive Git, financial truth decisions, merge conflict, high-risk cleanup, owner-boundary decision | high reasoning model plus review-board | Small models cannot make final decision. Review board or owner decision required. |

## Template Fields

Add to task cards and worker briefs:

```yaml
task_tier: small | medium | large | critical
recommended_model: mini | standard | high_reasoning
final_decision_owner: orchestrator | review_board | Orlando
worker_model_allowed: mini | standard | high_reasoning
worker_decision_limit: evidence_only | bounded_implementation | recommendation_only
```

## Routing Rules

- Use small/cheap workers for bounded evidence gathering, file inventories,
  grep passes, JSON parsing, and report summarization.
- Use standard coding model for one/two-file implementation with focused tests.
- Use high reasoning model for architecture, schema, financial truth, merge
  readiness, destructive operations, and owner-boundary decisions.
- Do not let small models make final decisions on high-risk work.
- For hard tasks, use a short strategy-bid stage: two or three workers propose
  compact plans; the orchestrator selects one and records why.
- Subagents should be delegated only when lanes are independent and isolated by
  worktree, branch, result file, and task-card allowlist.

## Review Board Trigger

Require `tenn-review-board` when:

- `task_tier: critical`
- financial truth canonical values are affected
- DB/runtime/source/data/destructive Git mutation is proposed
- merge/rebase/cherry-pick conflicts require judgement
- cleanup/deletion is proposed
- owner-boundary or stale-work adoption decision is unresolved

## Closeout Requirement

Every `large` or `critical` report should state:

- selected model tier
- why lower tier was insufficient
- worker roles used, if any
- final decision owner
- whether review-board was required and run
