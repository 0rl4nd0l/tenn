# Worker Task

worker_id: <stable-worker-id>
task_tier: <small|medium|large|critical>
decision_limit: <evidence_only|recommendation_only|bounded_implementation|strategy_bid>
permission_profile: <readonly>
agent: <evidence-scout|docs-scout|validation-scout|other>
model: <provider/model>
workdir: <repo-or-worktree-path>

## Objective

<One bounded worker objective.>

## Allowed Evidence

- <repo-relative file or directory>

## Hard Boundaries

- Read, grep, glob, and summarize only.
- Do not edit repo source, docs, templates, config, runtime files, or
  host-global files.
- Do not run git mutation commands.
- Evidence-only workers require verified OpenCode read-only permission
  enforcement, not prompt text alone.
- Do not inspect secrets, credentials, API keys, `.env` files, private tokens,
  raw DB dumps, production data, or runtime state.
- Record `DATA_MISSING` instead of guessing.
- Codex is the final decision-maker.

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
