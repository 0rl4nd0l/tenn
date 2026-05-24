---
job_id: post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524
title: Post QuantDinger milestone dirt hygiene audit
owner: Codex
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524
allowed_files:
  - docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/**
---

# Post QuantDinger Milestone Dirt Hygiene Audit

## Objective

Audit and classify the remaining uncommitted task-card and milestone dirt in the current worktree after the QuantDinger stop-hook warning. This is report-only preservation and must not clean, stage, commit, delete, stash, reset, move, rename, or format unrelated files.

## Scope

Allowed writes are limited to this task card and report artifacts under:

- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/`

Read-only inspection may include git status, worktree/branch history, task-card validation, registry listing and overlap checks, hook posture checks, task-card headers, matching report directories, branch/worktree names, and merge-parking registry presence.

## Hard Stops

Stop and report only if task-card validation fails due to unsafe scope, an active registry overlap involving this card's allowed files is HIGH, or required evidence would require modifying unrelated files, production data, DB/Qdrant/news/memory, canonical financial truth, parser routing, runtime bindings, migration state, Docker services, or destructive git operations.

## Required Outputs

- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/README.md`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/status.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/file_classification.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/validation.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/diff-check.json` if written by the repo tool

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
- JSON parse generated JSON artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
