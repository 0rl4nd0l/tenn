---
job_id: strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524
title: Strategy Lab QuantDinger complete next phases preserve or archive
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524.md
  - docs/agent_tasks/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_complete_and_next_phases_v1_20260524/**
  - reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524/**
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Strategy Lab QuantDinger Complete Next Phases Preserve Or Archive

## Objective

Resolve exactly the loose `strategy_lab_quantdinger_complete_and_next_phases_v1_20260524` milestone bundle by either preserving it as historical Strategy Lab / QuantDinger evidence or writing an archive recommendation report. Do not touch unrelated dirty task cards or runtime/product/data surfaces.

## Scope

Allowed writes are limited to this task card, the source QuantDinger complete-and-next-phases task card and matching report bundle, and this task's report bundle. The work may stage and commit only files under those allowed paths if the bundle is coherent and useful enough to preserve.

## Decision Rules

- Preserve by exact narrow commit if the source card and report bundle are coherent, validated, and useful historical QuantDinger / Strategy Lab evidence.
- Do not delete stale or superseded evidence. If later read-only sidecar smoke proof supersedes the bundle and preservation is not warranted, write an archive recommendation under this task output directory only.
- Stop with `DATA_MISSING` if the source bundle is incomplete or contradictory.

## Forbidden

- Do not touch foreign dirty task cards.
- Do not modify DB, Qdrant, news, memory, canonical financial truth, runtime, model, Cockpit implementation, Docker, container, external clone, pull, or service state.
- Do not execute sidecar smoke or set sidecar availability flags.
- Do not update Strategy Lab metadata.
- Do not use broad cleanup, stash, reset, delete, or `git add -A`.

## Required Outputs

- `reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524/status.json`
- `reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524/validation.json`
- `reports/agent_jobs/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524/diff-check.json` if written by the repo tool

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524.md`
- JSON parse for all JSON artifacts touched or preserved.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524.md --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_quantdinger_complete_next_phases_preserve_or_archive_v1_20260524.md --repo-root .` if available.
