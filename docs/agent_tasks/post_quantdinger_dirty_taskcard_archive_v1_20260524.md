---
job_id: post_quantdinger_dirty_taskcard_archive_v1_20260524
title: Post QuantDinger dirty task-card archive
owner: Codex
lane: Reporting
supporting_lanes:
  - Evaluation
  - Provenance
mutation_mode: safe_extension
approval_required: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524
allowed_files:
  - docs/agent_tasks/post_quantdinger_dirty_taskcard_archive_v1_20260524.md
  - docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/README.md
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/status.json
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/file_classification.json
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/validation.json
  - reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/diff-check.json
  - reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/README.md
  - reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/status.json
  - reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/validation.json
  - reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/diff-check.json
---

# Post QuantDinger Dirty Task-Card Archive

## Objective

Preserve the remaining post-QuantDinger dirty task-card bundle as historical
provenance only. Do not touch runtime, Strategy Lab implementation files,
QuantDinger runtime, Cockpit implementation files, parser routing, DB, Qdrant,
news, memory, canonical financial truth, Docker, broker, trading, paper-order,
model, GPU, or unrelated dirty task-card surfaces.

## Scope

Allowed writes are limited to this archive task card, the prior
post-QuantDinger milestone dirt hygiene audit task card, the prior audit report
files enumerated in frontmatter, and this archive task's report files
enumerated in frontmatter.

The current exact preservation candidate is:

- `docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/README.md`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/status.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/file_classification.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/validation.json`
- `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/diff-check.json`

## Decision Rules

- Preserve if the prior bundle is complete enough to explain the
  post-QuantDinger stop-hook dirt state and is bounded to task-card/report
  provenance.
- Archive-only if the prior bundle is useful only as historical context and no
  implementation follow-up should execute from it.
- Leave untouched and report if any candidate is not clearly post-QuantDinger
  or Strategy Lab/QuantDinger provenance.
- Do not modify already-committed Strategy Lab or QuantDinger implementation
  files.

## Forbidden

- No Docker or runtime startup.
- No broker, trading, paper-order, or QuantDinger runtime surfaces.
- No Tenn DB, Qdrant, news, memory, canonical financial truth, parser routing,
  runtime/model/GPU config, or Cockpit implementation changes.
- No unrelated A2M, gold, memory, source-label, trust-foundation, chat-guard,
  disk-pressure, docker-prune, SSH, repo-orchestration, or other task-card
  cleanup.
- No broad cleanup, deletion, stash, reset, rename, or `git add -A`.

## Required Checks

- Preflight branch, HEAD, status, worktree list, recent commits.
- Validate this task card before preserving artifacts.
- Registry `list-active` and `check-overlap` if available.
- Inspect current dirty files and confirm the final exact allowlist.
- Parse JSON artifacts touched or preserved.
- Run `git diff --check`.
- Run `check-diff` and report unrelated dirty-file blockers without cleaning
  them.
- Before commit, verify staged files are a subset of this task card's
  `allowed_files`.

## Deliverables

- `reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/README.md`
- `reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/status.json`
- `reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/validation.json`
- `reports/agent_jobs/post_quantdinger_dirty_taskcard_archive_v1_20260524/diff-check.json`
