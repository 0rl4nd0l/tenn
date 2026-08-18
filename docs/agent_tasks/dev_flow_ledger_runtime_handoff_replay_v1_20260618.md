---
job_id: dev_flow_ledger_runtime_handoff_replay_v1_20260618
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_ledger_runtime_handoff_replay_v1_20260618
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md
  - .agents/skills/tenn-explain/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-handoff/SKILL.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - docs/agent_registry/task_ledger/LEDGER.jsonl
  - docs/agent_registry/task_ledger/LEDGER.md
  - docs/agent_registry/task_ledger/README.md
  - docs/agent_tasks/dev_flow_ledger_runtime_handoff_v1_20260617.md
  - docs/dev_flow/templates/HANDOFF.md
  - docs/dev_flow/templates/TASK_LEDGER_ENTRY.json
  - docs/dev_flow/templates/TASK_LEDGER_SUMMARY.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_replay_v1_20260618/README.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_replay_v1_20260618/VALIDATION.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_replay_v1_20260618/PR_REPLAY.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/HANDOFF_SKILL.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/HOST_HANDOFF_PATCH.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/LEDGER_RUNTIME.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/NEXT_STEPS.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/README.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/SESSION_ID_TRACE.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/SUBAGENT_RESULTS.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/VALIDATION.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/WORKER_RESULT_ARCHITECTURE_REVIEW.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/WORKER_RESULT_GIT_HYGIENE_SESSION_TRACE.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/WORKER_RESULT_HANDOFF_SKILL.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/WORKER_RESULT_LEDGER_RUNTIME.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/WORKER_RESULT_VALIDATION_REVIEW.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/ARCHITECTURE_NOTES.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/HANDOFF.md
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/LEDGER_ENTRY.json
  - reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/NEXT_GOAL.md
  - scripts/agent_task_ledger.py
  - tests/test_agent_task_ledger.py
---

# Dev Flow Ledger Runtime Handoff Replay V1

## Objective

Replay PR #367's task-ledger runtime and handoff workflow onto latest canonical
after PRs #368, #370, #373, and #374 made the original PR dirty.

## Scope

- Preserve the still-relevant task-ledger runtime, ledger docs/templates, tests,
  and repo-native handoff skill from PR #367.
- Keep canonical docs-impact, model-routing, OpenCode bridge, and validation
  environment autonomy guidance already merged by later PRs.
- Use a clean sibling worktree from latest canonical. Do not touch the original
  dirty checkout or force-push the original PR #367 branch.

## Hard Boundaries

- Do not touch Tenn product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not mutate host-global files.
- Do not clean, reset, stash, delete, or modify the original dirty checkout.
- Do not merge PRs.
- Do not force-push the original PR #367 branch.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- Focused task-ledger unit tests.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
- `git diff --check`
- Final `git status --short --untracked-files=all`

## Definition Of Done

- PR #367's relevant control-plane work is replayed onto canonical without
  reverting later PRs.
- Focused validation passes or blockers are documented.
- A replacement PR is opened from a clean replay branch.
- Original dirty checkout and original PR #367 branch are untouched.
