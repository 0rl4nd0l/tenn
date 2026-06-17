---
job_id: dev_flow_opencode_worker_bridge_v1_20260617
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md
  - scripts/opencode_worker_bridge.py
  - tests/test_opencode_worker_bridge.py
  - .agents/skills/codex-worker-bridge/SKILL.md
  - docs/dev_flow/templates/WORKER_TASK.md
  - docs/dev_flow/templates/OPENCODE_WORKER_META.json
  - docs/dev_flow/worker_bridge/README.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/PREFLIGHT.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/DECISIONS.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/VALIDATION.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/README.md
---

# Dev Flow OpenCode Worker Bridge V1

## Objective

Add generic Codex development tooling for safe, read-only OpenCode worker
delegation. The bridge is for Codex/OpenCode/DeepSeek worker scouting tasks
while Tenn remains only the project under development.

## Scope

Allowed:

- Add `scripts/opencode_worker_bridge.py`.
- Add focused tests for bridge probing, worker output creation, result
  validation, ledger JSON shape, denylist behavior, and safe command
  construction.
- Add a repo-backed `codex-worker-bridge` skill.
- Add non-colliding worker task and metadata templates.
- Add a bridge README and closeout report bundle.

Intentionally out of scope:

- `docs/dev_flow/templates/MODEL_ROUTING.md`, because PR #368 is already the
  active docs-freshness/model-routing lane.
- `docs/dev_flow/templates/WORKER_RESULT.md`, because PR #368 is already
  editing that template. The bridge still creates and validates per-worker
  `WORKER_RESULT.md` artifacts in each worker job directory.
- Host-global OpenCode agent creation.
- Write-workers or source-editing workers.

## Boundaries

- This is generic Codex development tooling, not Tenn product/runtime code.
- Do not touch product, backend, frontend, runtime, data, extraction, source
  PDF, gold-label, prompt, DB, Qdrant, Redis, news, memory, service,
  model/GPU, backfill, production-data, or live-service state.
- Do not edit `.env`, secrets, credentials, API keys, private tokens, raw DB
  dumps, or host-global configuration.
- Do not commit, push, merge, clean, reset, stash, delete, rebase, or prune from
  the bridge runtime.
- Do not create global OpenCode agents in this task. Document commands only.
- Do not make DeepSeek/OpenCode workers final decision-makers for critical work.

## Preflight Requirements

- Fetch `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Work from a clean sibling worktree on
  `control-plane/opencode-worker-bridge-v1-20260617`.
- Verify PR #367 and decide whether this task depends on it.
- Check PR/session overlap for docs freshness and model routing.
- Check registry and task ledger availability.
- Search branches, worktrees, reports, task cards, PRs, issues, and scripts for
  existing OpenCode/DeepSeek worker bridge work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md`
- `python3 -m py_compile scripts/opencode_worker_bridge.py`
- Focused pytest or unittest for `tests/test_opencode_worker_bridge.py`.
- Parse changed skill frontmatter.
- JSON template validation.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md --no-write-report`
- `git diff --check`
- Changed-path guard.
- Product/runtime/data/extraction/count-24 guard.
- Dependency/lockfile guard.
- Host-global guard.

## Definition Of Done

- A generic read-only OpenCode worker bridge exists.
- DeepSeek/OpenCode worker delegation is documented and validated.
- Workers produce structured result artifacts.
- Codex remains final decision-maker.
- No Tenn product/runtime/extraction mutation occurred.
- If validation passes, commit locally, push the branch, and open a PR against
  `migration/clean-runtime-baseline-reconstruct-v1`.
