---
job_id: extraction_broad_run_saved_artifact_fixture_replay_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/GUARD.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/VALIDATION.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/PR_REVIEW.md
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/fixture_broad_run_record.json
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/fixture_summary.json
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/fixture_assertions.json
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/validation.json
  - reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: false
---

# Extraction Broad-Run Saved Artifact Fixture Replay

## Objective

Run one bounded no-canonical-write saved-artifact fixture replay against the
broad-run provenance/risk surface from commit `deba6e0b`. Emit and inspect a
broad-run-shaped record for an existing saved artifact without running
extraction, broad samples, runtime services, or data-store writes.

## Source Artifact

Use:

`reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json`

Reason: this artifact already contains real saved extraction output fields:
`metrics`, `row_refs`, `field_provenance`, `metric_source_scales`,
`metric_scale_sources`, `scale_validation`, status, ticker, document id, and
source provenance.

## Hard Stops

- Do not run `run_multipass_extraction`.
- Do not run count-24, count-32, random samples, broad extraction, broad
  backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, model/GPU/service config, production data, GitHub, or
  remote branches.
- Do not change source code in this validation slice.

## Required Output

- `fixture_broad_run_record.json`: one broad-run-shaped record using the saved
  artifact and the current helper contract.
- `fixture_summary.json`: `compute_summary([record])` output.
- `fixture_assertions.json`: machine-readable assertions for
  `metric_provenance`, `provenance_missing`,
  `accepted_output_scale_magnitude_risk`, and summary rollups.
- Standard guard, state, decisions, validation, review, and next-goal notes.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --write-report`
- Execute one inline no-extraction saved-artifact fixture replay.
- Parse and assert the generated JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --repo-root .`
