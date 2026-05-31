---
job_id: next5_existing_evidence_closeout_v1_20260531
title: Next Five Existing Evidence Closeout v1
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Runtime
  - Evaluation
  - Repo Hygiene
  - Provenance
  - Memory
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531
allowed_files:
  - docs/agent_tasks/next5_existing_evidence_closeout_v1_20260531.md
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/README.md
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/status.json
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/issue_closeout_matrix.md
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/validation.json
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/diff-check.json
  - reports/agent_jobs/next5_existing_evidence_closeout_v1_20260531/code_review.json
allow_audit_code_changes: true
---

# Next Five Existing Evidence Closeout v1

Close the safe existing-evidence portion of the next-five issue set after #74.

## Scope

Evaluate and close only issues that already have current, GitHub-visible
evidence on this branch:

- #112 `[Runtime] Add final-status observability for nightly news scheduling`
- #114 `[Runtime] Nightly news fetch fails because canonical ASX ticker universe is missing`
- #115 `[Repo Hygiene] Add report-only Codex nightly lock-up audit`

Record why #71 and #88 remain the next unresolved issues but are not included in
this closeout slice:

- #71 still requires a source-label fixture/test task card or equivalent
  committed matrix.
- #88 still requires the memory-system fitness audit report.

## Allowed GitHub Actions

If validation confirms the evidence is current and visible, Codex may:

- comment on #112, #114, and #115 with closeout evidence;
- close #112, #114, and #115;
- add status comments to #71 and #88 only if needed.

No labels, milestones, PR creation, branch cleanup, merge, rebase, reset, stash,
prune, delete, cherry-pick, or production data mutation is authorized.

## Required Validation

- Task-card validate.
- Registry list-active and overlap check.
- Evidence visibility for commit `3725591cf76e`.
- Existing report artifact presence/JSON parse where applicable.
- `financial-engine_v2/scripts/nightly_news.sh` shell syntax check.
- `financial-engine_v2/data/raw/asx_ticker_universe.txt` present with expected
  SHA-256 from issue evidence.
- `git diff --cached --check`.
- Task-card `check-diff`.
- Registry release.

## Hard Boundaries

Do not change:

- product/backend/frontend/runtime code;
- production DB/Qdrant/news/memory stores;
- canonical financial truth;
- parser routing, extraction prompts, or gold labels;
- runtime/model/GPU/service config;
- installed cron/systemd timers;
- unrelated dirty files.

## System Contract Compliance

Target system layer: Reporting/issue closeout evidence only. This task does not
run ingestion, extraction, storage, retrieval, analysis, or client mutation.

Relevant contract rules:

- Backend authority and pipeline order remain unchanged.
- No fallback, substitution, duplicate retrieval, canonical write, or
  data-store mutation is introduced.

GPU guard: not required. This task does not spawn, restart, or depend on
llama-server.
