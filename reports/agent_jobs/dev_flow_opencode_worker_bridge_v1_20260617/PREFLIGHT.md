# Preflight

## Repo State

- Source checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Source branch: `control-plane/dev-flow-agent-task-ledger-v1-20260616`
- Source HEAD: `137535b81a5b60d1f94ca630605caadccc4e1b99`
- Source dirty state:
  - `.agents/skills/tenn-fix/SKILL.md`
  - `.agents/skills/tenn-git-guard/SKILL.md`
  - `.agents/skills/tenn-worker/SKILL.md`
  - `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`
  - `docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md`

## Canonical Base

- Fetched: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Canonical base used for sibling worktree:
  `6eff52404af61b9717bffb5a250e06209713d517`
- Worktree:
  `/home/l4nd0/tenn-opencode-worker-bridge-v1-20260617`
- Branch:
  `control-plane/opencode-worker-bridge-v1-20260617`

## Registry And Ledger

- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  returned `ok: true` and `active_jobs: []`.
- Registry root:
  `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- Live task ledger:
  `DATA_MISSING`
- Durable task ledger:
  `DATA_MISSING`

PR #367 adds `scripts/agent_task_ledger.py` and task-ledger docs, but it is
still open. This bridge does not depend on PR #367; it emits ledger-compatible
JSON and marks ledger script availability in output.

## PR And Duplicate Checks

- PR #367: open, base
  `migration/clean-runtime-baseline-reconstruct-v1`, head
  `control-plane/agent-ledger-runtime-handoff-v1-20260617`.
- PR #368: open, base
  `migration/clean-runtime-baseline-reconstruct-v1`, head
  `control-plane/docs-freshness-model-routing-v1-20260617`.
- PR #368 edits `docs/dev_flow/templates/MODEL_ROUTING.md` and
  `docs/dev_flow/templates/WORKER_RESULT.md`.

Duplicate-work classification: `pass_with_collision_avoidance`.

Existing related surfaces:

- `agent-orchestrator/src/server/adapters/opencode.ts`
- `scripts/opencode-server`
- `opencode.json`

No equivalent `scripts/opencode_worker_bridge.py`, bridge task card, bridge
report bundle, or matching OpenCode/DeepSeek worker bridge PR was found.
