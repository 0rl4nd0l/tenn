---
job_id: extraction_deployment_readiness_current_canonical_v1_20260609
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_deployment_readiness_current_canonical_v1_20260609.md
  - reports/agent_jobs/extraction_deployment_readiness_current_canonical_v1_20260609/README.md
  - reports/agent_jobs/extraction_deployment_readiness_current_canonical_v1_20260609/status.json
  - reports/agent_jobs/extraction_deployment_readiness_current_canonical_v1_20260609/validation.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_deployment_readiness_current_canonical_v1_20260609
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
---

# Extraction Deployment Readiness Current Canonical Audit

## Objective

Analyze why financial metric extraction is still inaccurate and not ready for
broad deployment using current-turn evidence from:

- Recently completed extraction work and merged PR/report artifacts.
- Current checkout, branch, HEAD, registry, and remote canonical status.
- Local uncommitted/dirty extraction-related worktrees and local-only packet
  branches.
- Existing bounded validation and scorecard evidence.

## Scope

Mode: AUDIT_ONLY and REPORT_LOCAL.

This task may read repository files, Git status, read-only registry state,
read-only GitHub issue/PR metadata, and existing report artifacts. It may write
only the task card and report-local status/validation artifacts listed in
`allowed_files`.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not implement production extraction repair.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, normal parser caches, services,
  model/GPU config, or production data.
- Do not create, edit, label, comment on, close, or reopen GitHub issues.
- Do not clean, stash, reset, merge, rebase, cherry-pick, delete branches, or
  delete unrelated dirt.

## Required Output

- Current checkout, registry, branch, HEAD, and remote-canonical evidence.
- Current GitHub issue/PR read-only status relevant to extraction readiness.
- Summary of recently completed extraction work and what it did or did not
  prove.
- Summary of dirty/local-only extraction work and why it is not deployment
  evidence.
- Root-cause analysis for continued extraction inaccuracy.
- Explicit next approval boundary for any future bounded count run.
- Validation evidence for the report-local artifacts.
