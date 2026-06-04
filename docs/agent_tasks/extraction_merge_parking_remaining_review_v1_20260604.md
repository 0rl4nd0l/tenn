---
job_id: extraction_merge_parking_remaining_review_v1_20260604
lane: Reporting
supporting_lanes:
  - Financial Truth
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
approval_required: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: none
allowed_files:
  - docs/agent_tasks/extraction_merge_parking_remaining_review_v1_20260604.md
  - reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/README.md
  - reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/status.json
  - reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/parking_decision_table.json
  - reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/next_actions.md
  - docs/agent_registry/merge_parking/REGISTRY.md
  - docs/agent_registry/merge_parking/parked/appendix5b-report-gate-refresh-v1-20260531.md
  - docs/agent_registry/merge_parking/parked/extraction-appendix4d-profit-after-tax-alias-v1-20260602.md
  - docs/agent_registry/merge_parking/parked/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602.md
  - docs/agent_registry/merge_parking/parked/extraction-broad-accuracy-push-v1-20260602.md
  - docs/agent_registry/merge_parking/parked/extraction-live-contract-truth-gates-v1-20260603-nvme.md
operator_approval_source: User requested audit-only extraction merge-parking continuation on 2026-06-04.
---

# Extraction Merge Parking Remaining Review V1

## Objective

Continue the Tenn extraction merge-parking review through the remaining parked
items, update scoped registry status notes, and produce safe continuation
prompts. This task is audit-only.

## Scope

- Use `origin/migration/clean-runtime-baseline-reconstruct-v1` as extraction
  canonical when confirming PR #293 and comparing parked extraction work.
- Review parked registry entries and local parked worktrees only.
- Treat dirty parent branches as containers, not merge units.
- Produce report artifacts and registry notes only.

## Hard Stops

- Do not merge, cherry-pick, rebase, or stage extraction branches.
- Do not edit extraction code.
- Do not run extraction, backfill, random samples, canaries, or broad merges.
- Do not mutate production DB, Qdrant, news, memory, source PDFs, prompts,
  gold labels, runtime config, schema, or unrelated dirty files.
- Do not clean, stash, reset, delete, or prune unrelated dirt.

## Required Output

- `reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/README.md`
- `reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/status.json`
- `reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/parking_decision_table.json`
- `reports/agent_jobs/extraction_merge_parking_remaining_review_v1_20260604/next_actions.md`
