---
job_id: extraction_merge_parking_registry_setup_v1_20260604
lane: Reporting
supporting_lanes:
  - Financial Truth
  - Evaluation
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_merge_parking_registry_setup_v1_20260604
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/extraction_merge_parking_registry_setup_v1_20260604.md
  - docs/agent_registry/merge_parking/REGISTRY.md
  - docs/agent_registry/merge_parking/parked/appendix5b-report-gate-refresh-v1-20260531.md
  - docs/agent_registry/merge_parking/parked/extraction-appendix4d-profit-after-tax-alias-v1-20260602.md
  - docs/agent_registry/merge_parking/parked/extraction-broad-accuracy-push-v1-20260602.md
  - docs/agent_registry/merge_parking/parked/extraction-data-missing-20260604.md
  - docs/agent_registry/merge_parking/parked/extraction-live-contract-truth-gates-v1-20260603-nvme.md
  - reports/agent_jobs/extraction_worktree_merge_parking_inventory_v1_20260604/**
  - reports/agent_jobs/extraction_merge_parking_registry_setup_v1_20260604/README.md
  - reports/agent_jobs/extraction_merge_parking_registry_setup_v1_20260604/status.json
  - reports/agent_jobs/extraction_merge_parking_registry_setup_v1_20260604/**
---

# Extraction Merge Parking Registry Setup

## Objective

Create visible merge-parking registry surfaces for Tenn extraction work so
completed-but-unmerged, needs-validation, high-risk parent-batch, and
data-missing findings from the extraction worktree inventory remain discoverable
inside the repo.

## Scope

- Read the existing extraction worktree inventory bundle only.
- Create `docs/agent_registry/merge_parking/REGISTRY.md` and
  `docs/agent_registry/merge_parking/parked/` if absent.
- Add evidence-backed parked entries only for the explicitly requested highest
  priority candidates.
- Preserve DATA_MISSING visibly.

## Hard Stops

- Do not merge or cherry-pick anything.
- Do not prune, delete, clean, stash, reset, or restore any worktree.
- Do not modify extraction code or touch dirty NVMe parent batch contents.
- Do not run extraction, backfill, samples, runtime mutation, DB/Qdrant/news
  mutation, source PDF edits, prompt changes, gold-label changes, or schema
  changes.

## Required Validation

- Markdown/report sanity check for created registry files.
- JSON validation for any created JSON artifacts.
- `git diff --check`
- `scripts/agent_job_contract.py check-diff`
- No extraction code changes.
- No source PDFs staged.
- Final `python3 scripts/agent_job_registry.py list-active`
- Final `git status`
