---
job_id: strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525
title: Strategy Lab readonly integration dirty task-card unblock
owner: Codex
lane: Reporting
primary_scope: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525
allowed_files:
  - docs/agent_tasks/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525.md
  - docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md
  - docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md
  - reports/agent_jobs/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525/**
---

# Strategy Lab Readonly Integration Dirty Task-Card Unblock

## Objective

Classify and safely preserve or archive-classify only the two dirty task cards
that blocked the Strategy Lab readonly subsystem maturation integration review:

- `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
- `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`

Do not integrate `e5e12fe990d1` in this task.

## Allowed Work

- Inspect the two dirty task cards and their existing report bundles.
- Classify lane and lifecycle state for each card.
- Preserve the two task cards unchanged if still useful, or classify them
  archive-only if stale.
- Write this task's report artifacts under its output directory.

## Forbidden

- Do not cherry-pick or merge `e5e12fe990d1`.
- Do not edit Strategy Lab UI, library, docs, reports, or tests from the source
  branch.
- Do not touch backend, runtime, parser, model, GPU config, DB, Qdrant, news,
  memory, source registry, or canonical financial truth.
- Do not modify worker provenance or full-system audit implementation surfaces.
- Do not clean, stash, reset, delete, or absorb unrelated dirty files.
- Do not create broad merge-parking infrastructure.

## Validation

- Validate this task card.
- Run registry `list-active` and `check-overlap`.
- Validate JSON artifacts created by this task.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Report final `git status --short --untracked-files=all`.

## Done Criteria

The two named dirty task cards are either committed/preserved/archive-classified
or explicitly reported as still blocking with exact reason. No other files are
touched.
