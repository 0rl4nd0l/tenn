---
job_id: dev_flow_opencode_worker_bridge_safety_fix_v1_20260618
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618.md
  - scripts/opencode_worker_bridge.py
  - tests/test_opencode_worker_bridge.py
  - .agents/skills/codex-worker-bridge/SKILL.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618/README.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618/STATE.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618/DECISIONS.md
  - reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618/VALIDATION.md
---

# Dev Flow OpenCode Worker Bridge Safety Fix V1

## Objective

Fix post-PR #370 OpenCode worker bridge review issues:

- Fail closed for `evidence_only` workers when attach mode or
  `OPENCODE_SERVER_URL` would be used without proven remote readonly
  enforcement.
- Treat the requested `decision_limit` from args/metadata as authoritative and
  reject worker output that reports a different limit.

## Scope

Allowed:

- Patch `scripts/opencode_worker_bridge.py`.
- Add focused unit tests in `tests/test_opencode_worker_bridge.py`.
- Clarify `.agents/skills/codex-worker-bridge/SKILL.md` only if needed.
- Maintain this task card and report bundle.

Out of scope:

- Tenn product/runtime/data/extraction/count-24 files.
- Host-global OpenCode config or agent files.
- Dependency files or lockfiles.
- Write-worker behavior.
- Merging PRs.

## Boundaries

- This is generic Codex development tooling, not Tenn runtime/product code.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs,
  gold-labels, extraction prompts, runtime state, model/GPU/service config, or
  production data.
- Do not clean, reset, stash, delete, rebase, merge, or prune worktrees.
- Preserve unrelated dirty state in other checkouts.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618.md`
- `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py`
- `python3 -m unittest tests.test_opencode_worker_bridge`
- Parse changed skill frontmatter if `.agents/skills/codex-worker-bridge/SKILL.md` changes.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618.md --no-write-report`
- `git diff --check && git diff --cached --check`
- Changed-path guard.
- Product/runtime/data/extraction/count-24 guard.
- Dependency/lockfile guard.
- Host-global guard.

## Definition Of Done

- P1 attach-mode safety issue is fixed.
- P2 decision-limit mismatch issue is fixed.
- Tests prove both failure modes.
- A new PR is open against `migration/clean-runtime-baseline-reconstruct-v1`.
- No Tenn product/runtime/extraction mutation occurred.
