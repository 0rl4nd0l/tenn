---
job_id: extraction_broad_run_provenance_risk_flags_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/GUARD.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/VALIDATION.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/PR_REVIEW.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/WORKER_provenance_inspection.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/WORKER_scale_risk_inspection.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/WORKER_test_design.md
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/validation.json
  - reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_run_provenance_risk_flags_v1_20260617
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# Extraction Broad-Run Provenance Risk Flags

## Objective

Implement the first bounded slice from the accepted-output scale/provenance
handoff: surface row-level provenance already present in broad-run extraction
payloads and add machine-readable accepted-output scale/magnitude risk flags
without changing canonical acceptance behavior.

## Current Evidence

- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`.
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`.
- Base and HEAD: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `6eff52404af61b9717bffb5a250e06209713d517`.
- Registry read-only returned `active_jobs: []`.
- Live Task Ledger: `DATA_MISSING`.
- Committed Task Ledger: `DATA_MISSING`.
- Fallback duplicate-work search found related merged/history work, but no open
  PR that already implements this post-PR365 broad-run output contract.

## Hard Stops

- Do not change extraction prompts, canonical persistence, validation gates, or
  accepted/rejected status semantics in this slice.
- Do not run count-24, count-32, random samples, broad backfill, full
  ticker-universe extraction, runtime/service jobs, or PR #318 patches.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, gold
  labels, schemas, model/GPU/service config, production data, GitHub, or
  remote branches.
- Stop on any required write outside `allowed_files`.

## Required Implementation

- Add focused RED/GREEN tests against `financial-engine_v2/scripts/broad_extraction_test.py`.
- Keep broad-run output generation no-write beyond its existing result-file
  behavior.
- Add per-metric output evidence for metrics already present in payloads:
  `row_ref`, excerpt/source snippet when present, page/table/source provenance
  when present, field provenance when present, and explicit
  `provenance_available` / `provenance_missing` signals.
- Add accepted-output scale/magnitude risk flags as machine-readable report
  fields. WHC/HCW/EDU/LBL evidence may shape fixtures, but implementation must
  be generic and must not special-case acceptance behavior.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md`
- Focused RED test before implementation.
- Focused GREEN test after implementation.
- `python3 -m py_compile financial-engine_v2/scripts/broad_extraction_test.py`
- `python3 -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md --repo-root .`
