---
job_id: extraction_pr129_base_sync_after_canary_preflight_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pr129_base_sync_after_canary_preflight_v1_20260529.md
  - reports/agent_jobs/extraction_pr129_base_sync_after_canary_preflight_v1_20260529/**
  - reports/agent_jobs/extraction_pr129_base_sync_after_canary_preflight_v1_20260529/README.md
  - reports/agent_jobs/extraction_pr129_base_sync_after_canary_preflight_v1_20260529/status.json
  - reports/agent_jobs/extraction_pr129_base_sync_after_canary_preflight_v1_20260529/diff-check.json
  - docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/**
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/README.md
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/status.json
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/preflight.json
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_pr129_base_sync_after_canary_preflight_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: branch_push_only
related_pr: 129
---

# Extraction PR129 Base Sync After Canary Preflight

## Objective

Restore PR #129 mergeability after the base branch advanced with the blocked
#96 third-canary runtime preflight report.

## Scope

- Primary lane: Evaluation.
- Mode: SAFE EXTENSION, branch-sync/report-only.
- Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`.
- Worktree:
  `/home/l4nd0/tenn-extraction-real-gold-corpus-baseline-v1-20260529`.

## Contract Check

Target system layer: Evaluation/reporting metadata only.

Relevant contract rules: backend remains sole authority; no extraction,
storage, retrieval, analysis, or client behavior changes.

What must not change: production code, source PDFs, parser routing, prompts,
gold labels, schemas/migrations, runtime/model/GPU/service config, DB/Qdrant/
news/memory stores, Cockpit UI, GitHub issue state, or canary execution.

Why safe: this task only merges the new base report commit into the PR branch
and preserves the blocked canary evidence so PR #129 can remain mergeable.

GPU process check required: no. This task does not start or depend on
llama-server.

## Validation

- Validate, check-overlap, and claim this task card.
- Merge `origin/migration/clean-runtime-baseline-reconstruct-v1` into the PR
  branch.
- Resolve only report/state conflicts if any.
- JSON validation for report artifacts.
- `git diff --check`.
- `git status --short --branch --untracked-files=all`.
- `git diff --cached --check`.
- Release registry claim.
- Commit and push the branch.
- Recheck PR #129 mergeability/checks.
