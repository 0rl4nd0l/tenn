---
job_id: dev_flow_worker_result_contract_hardening_v1_20260701
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_worker_result_contract_hardening_v1_20260701.md
  - scripts/opencode_worker_bridge.py
  - tests/test_opencode_worker_bridge.py
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/worker_bridge/README.md
  - docs/dev_flow/OPENCODE_WORKER_BRIDGE_RUNBOOK.md
  - .agents/skills/codex-worker-bridge/SKILL.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/README.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/STATE.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/DECISIONS.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/VALIDATION.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/PR_REVIEW.md
  - reports/agent_jobs/dev_flow_worker_result_contract_hardening_v1_20260701/LEDGER_ENTRY.json
---

# Dev Flow Worker Result Contract Hardening V1

## Objective

Harden Tenn worker-result validation for the two failure classes observed in
`reports/agent_jobs/codex_workflow_best_practices_research_v1_20260701/`:

- A worker result wrapped in a markdown fence can parse
  `stop_condition_hit` as `no\n```` instead of the exact value `no`.
- `evidence_only` validation can flag advisory text that names final-authority
  boundaries as if the worker claimed final authority.

## Scope

Allowed:

- Patch `scripts/opencode_worker_bridge.py`.
- Add focused unit tests in `tests/test_opencode_worker_bridge.py`.
- Clarify worker-result docs, templates, or the bridge skill only if behavior or
  operator expectations change.
- Maintain this task card and report bundle.

Out of scope:

- Tenn product/runtime/data/extraction/parser/prompt/source-PDF/gold-label code
  or data.
- DB, Qdrant, Redis, news stores, memory stores, services, Docker volumes,
  model/GPU config, host-global Codex/OpenCode config, or secrets.
- GitHub writes.
- Commits, pushes, merges, rebases, resets, stashes, cleanup, branch deletion,
  worktree deletion, pruning, or force operations.
- Broad workflow redesign beyond this worker-result contract slice.

## Boundaries

- Preserve `/home/l4nd0/tenn` unrelated dirt.
- Preserve
  `/home/l4nd0/tenn-codex-workflow-best-practices-research-v1-20260701` as the
  research handoff worktree.
- Keep worker validation fail-closed: malformed or unsafe results must still be
  rejected.
- Do not make workers final authority for scope, readiness, or integration.
- Do not mutate the live task ledger; record report-local ledger intent instead.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_worker_result_contract_hardening_v1_20260701.md`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "worker-result contract hardening stop_condition_hit evidence_only final authority" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- Red/green focused unit tests for the two observed failure classes.
- `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py`
- `python3 -m unittest tests.test_opencode_worker_bridge`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_worker_result_contract_hardening_v1_20260701.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_worker_result_contract_hardening_v1_20260701.md --no-write-report`
- `git diff --check`
- `git status --short --untracked-files=all`

## Definition Of Done

- Focused regression tests cover fenced worker output whose last field is
  `stop_condition_hit: no`.
- Focused regression tests cover an `evidence_only` worker result that discusses
  final-authority boundaries without claiming final authority.
- The validator still rejects genuine final-authority claims under
  `evidence_only`.
- Focused validation passes.
- Docs impact is recorded, with docs changed only if the contract changed.
- No product/runtime/data/extraction, host-global, GitHub, or Git history
  mutation occurs.
