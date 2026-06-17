---
job_id: extraction_broad_run_positive_risk_fixture_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/GUARD.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/VALIDATION.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/PR_REVIEW.md
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/positive_fixture_input.json
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/positive_broad_run_record.json
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/positive_summary.json
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/positive_assertions.json
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/validation.json
  - reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_broad_run_positive_risk_fixture_v1_20260617
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# Extraction Broad-Run Positive Risk Fixture

## Objective

Add one exact no-extraction positive fixture for the broad-run
`accepted_output_scale_magnitude_risk` surface. The fixture must exercise
machine-readable risk flags and summary rollups without running extraction,
broad samples, runtime services, or data-store writes.

## Fixture Source

Use an exact synthetic fixture committed only as a report artifact. This follows
the prior `NEXT_GOAL.md` allowance for an exact synthetic fixture when no
existing saved artifact with mixed source scales is selected.

## Hard Stops

- Do not run `run_multipass_extraction`.
- Do not run count-24, count-32, random samples, broad extraction, broad
  backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, model/GPU/service config, production data, GitHub, or
  remote branches.
- Do not change source code in this validation slice.

## Required Output

- `positive_fixture_input.json`: exact fixture payload.
- `positive_broad_run_record.json`: one broad-run-shaped accepted-output record
  generated through current helper contracts.
- `positive_summary.json`: `compute_summary([record])` output.
- `positive_assertions.json`: machine-readable assertions for risk flags and
  summary `risk_flag_distribution`.
- Standard guard, state, decisions, validation, review, and next-goal notes.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --write-report`
- Execute one inline no-extraction positive fixture replay.
- Parse and assert generated JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --repo-root .`
