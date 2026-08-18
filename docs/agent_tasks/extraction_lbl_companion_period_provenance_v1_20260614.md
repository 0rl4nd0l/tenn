---
job_id: extraction_lbl_companion_period_provenance_v1_20260614
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/README.md
  - reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/status.json
  - reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/validation.json
  - reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# Extraction LBL Companion Period Provenance

## Objective

Implement the approved narrow LBL companion-source period provenance rule:
bind a half-year presentation's `period_end` from same-day issuer companion
source evidence only with explicit cross-document provenance, while preserving
target table-local scale. Do not hardcode LBL's date.

## Scope

Worktree:
`/home/l4nd0/tenn-lbl-companion-period-provenance-v1-20260614`.

Branch:
`safe/extraction-lbl-companion-period-provenance-v1-20260614`.

Base commit:
`efd11b9a44d9d73bf94b86f6d90c8f75342bb0cf`.

Mode: SAFE_EXTENSION / STRICTLY BOUNDED / TDD.

## Input Evidence

- Design report:
  `/home/l4nd0/tenn-lbl-source-provenance-design-v1-20260614/reports/agent_jobs/extraction_lbl_source_provenance_design_v1_20260614/README.md`.
- Prior period evidence audit:
  `/home/l4nd0/tenn-lbl-period-evidence-audit-v1-20260614/reports/agent_jobs/extraction_lbl_period_evidence_audit_v1_20260614/README.md`.
- User approval: `approve`.
- User approval on 2026-06-15: targeted LBL extraction canary and PR publish
  are explicitly approved after focused unit validation and code review.

## Hard Stops

- Do not run count-24, count-32, random samples, broad replays, backfills,
  service routes, or production mutations.
- Runtime extraction validation is limited to one targeted report-local LBL
  canary for
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/financial_performance/2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf`
  with `DATA_ROOT` redirected outside the repo. Do not persist results to DB or
  production runtime stores.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, runtime config, model config, or GPU/service config.
- Do not mine PR #318 patches.
- Do not close, comment on, edit, merge, or supersede PR #340 without explicit
  approval.
- Do not hardcode LBL's `2025-12-31` date outside source-bound test fixtures.
- Do not copy companion-source narrative scale onto target presentation metrics.

## Required Implementation

- Add focused RED tests before implementation.
- Keep the implementation in `multipass_extraction.py`.
- Bind companion period evidence only when:
  - target title has a half-year hint;
  - target period end equals the leading announcement date;
  - target source text lacks exact source-bound period-end evidence;
  - companion evidence is exact source-text period-end evidence;
  - companion period type is `H`;
  - companion source is same-ticker and same announcement date;
  - all companion period sources agree.
- Record explicit cross-document provenance in `source_period_end_binding`.
- Preserve target metric-local scale behavior.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md`
- RED focused test command before implementation.
- GREEN focused test command after implementation.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md --repo-root .`
- One approved targeted LBL canary may be run after code review with external
  cache/status artifacts redirected outside the repo and summarized in the
  report packet.
