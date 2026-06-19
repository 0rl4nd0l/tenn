# Worker Task

Use this template instead of a visible `tenn-worker` skill. Workers are backend
delegations from `/fix`, `/review-board`, or a task-card-approved orchestrator.

worker_id: <stable-worker-id>
lane: <one independent lane>
task_tier: <small|medium|large|critical>
decision_limit: <evidence_only|recommendation_only|bounded_implementation|strategy_bid>
permission_profile: <readonly|bounded_write>
agent: <evidence-scout|docs-scout|validation-scout|other>
model: <provider/model>
workdir: <repo-or-worktree-path>
branch: <branch-name>
task_card: <repo-relative task-card path>
allowed_files:
- <exact repo-relative path, required for bounded_implementation>
validation_expected:
- <command or DATA_MISSING>
result_path: <repo-relative WORKER_RESULT.md path>
stop_condition: <exact condition requiring stop/escalation>

## Objective

<One bounded worker objective.>

## Allowed Evidence And Files

- <repo-relative file or directory>

## Hard Boundaries

- One worker, one lane, one worktree, one result file.
- The lane must be independent from other workers' mutation and decision
  surfaces.
- Workers must not share mutation surfaces.
- Evidence-only, recommendation-only, and strategy-bid workers read, grep,
  glob, and summarize only.
- Bounded-implementation workers may edit only the exact assigned
  `allowed_files`, run the assigned validation, and report every changed,
  generated, skipped, or dirty path in `WORKER_RESULT.md`.
- Do not edit repo source, docs, templates, config, runtime files, or
  host-global files unless the brief explicitly lists those repo-relative files
  and sets `decision_limit: bounded_implementation`.
- Do not run git mutation commands.
- Evidence-only workers require verified OpenCode read-only permission
  enforcement, not prompt text alone.
- Do not inspect secrets, credentials, API keys, `.env` files, private tokens,
  raw DB dumps, production data, or runtime state.
- Record `DATA_MISSING` instead of guessing.
- Codex is the final decision-maker.
- Stop at the named stop condition and return a result instead of widening
  scope.

## Required Output

Return `WORKER_RESULT.md` content with:

- `worker_id`
- `task_tier`
- `model`
- `decision_limit`
- `summary`
- `findings`
- `evidence_paths`
- `confidence`
- `risks`
- `recommended_next_action`
- `stop_condition_hit` (`yes`, `no`, or `DATA_MISSING` exactly)

When `stop_condition_hit` is `yes`, explain the condition and impact in
`WORKER_RESULT.md`.
