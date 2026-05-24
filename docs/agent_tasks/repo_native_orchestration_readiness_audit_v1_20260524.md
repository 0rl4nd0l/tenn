---
job_id: repo_native_orchestration_readiness_audit_v1_20260524
title: Repo-native orchestration readiness audit
owner: Codex
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Memory
  - Provenance
  - Repo Hygiene
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524
allowed_files:
  - docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md
  - reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/README.md
  - reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/status.json
  - reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/validation.json
  - reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/diff-check.json
---

# Repo-Native Orchestration Readiness Audit

## Objective

Audit Tenn's current repo-native orchestration machinery and produce a concrete implementation plan for moving from prompt/source-based orchestration toward durable repo-native goal files, machine-checkable task cards, shared registry visibility, merge parking, checkpoint/status schemas, hooks, and CI validation.

## Scope

This is report-only work. Inspect repo docs, agent instructions, task-card files, registry/contract/hook scripts, local hook configs, CI workflows, git ignore/exclude behavior, report/status artifacts, and existing goal/merge/checkpoint conventions.

Allowed writes are limited to this task card and report artifacts under:

- `reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/`

## Hard Stops

Stop and report only if a required finding would require product/backend/frontend/runtime implementation, parser routing changes, financial-truth changes, memory writes, Qdrant or database mutation, news/store mutation, Docker/cron/systemd/model/GPU changes, destructive git operations, unrelated dirty-file cleanup, merge/cherry-pick/rebase/reset/stash, or a new orchestration framework.

If registry overlap or check-diff fails solely because unrelated pre-existing dirty/untracked files are outside this card, record that as environmental collision evidence and do not clean those files.

## Required Outputs

- `reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/README.md`
- `reports/agent_jobs/repo_native_orchestration_readiness_audit_v1_20260524/status.json`
- Tool-generated validation and diff-check artifacts if available.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md` if overlap permits
- JSON parse generated JSON artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md`
