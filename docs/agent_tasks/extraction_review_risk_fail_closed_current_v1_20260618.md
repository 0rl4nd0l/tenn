---
job_id: extraction_review_risk_fail_closed_current_v1_20260618
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/README.md
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/STATE.md
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/DECISIONS.md
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/VALIDATION.md
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/NEXT_GOAL.md
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/saved_artifact_replay.py
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/saved_artifact_replay.json
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/validation.json
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/diff-check.json
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/status.json
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/registry_claim.json
  - reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/registry_release.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Review-Risk Fail-Closed Current Canonical

## Objective

Replay the validated local accepted-output review-risk fail-closed broad-run
gate onto current canonical and prove behavior with a no-extraction
saved-artifact replay over the approved count-24 output.

## Scope

Worktree:
`/home/l4nd0/tenn-review-risk-fail-closed-current-v1-20260618`

Branch:
`safe/extraction-review-risk-fail-closed-current-v1-20260618`

Base:
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`e555f540019a50462da1596a6c2986260468b4d8`.

Source preserve candidate:
`/home/l4nd0/tenn-review-risk-fail-closed-v1-20260618`

Owner approval update:
The owner approved GitHub mutation after local commit preservation on
2026-06-18. The approval is limited to pushing this branch and opening a PR for
this bounded diff.

## Read-Only Inputs

- `/home/l4nd0/tenn-count24-current-canonical-execution-v1-20260617/reports/agent_jobs/extraction_count24_current_canonical_execution_v1_20260617/sample_results.json`
- `/home/l4nd0/tenn-count24-current-canonical-execution-v1-20260617/reports/agent_jobs/extraction_count24_current_canonical_execution_v1_20260617/summary.json`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/extraction_full_broad_accuracy_review_board_v1_20260618/BOARD_DECISION.json`

## Required Change

- In `financial-engine_v2/scripts/broad_extraction_test.py`, reclassify only
  already-accepted broad-run rows whose
  `accepted_output_scale_magnitude_risk.risk_level` is `review` as failed with
  `validation_gate:accepted_output_scale_magnitude_risk:<codes>`.
- Preserve risk/provenance metadata on the row.
- Keep `risk_level == "info"` rows accepted.
- Add/keep focused tests in
  `financial-engine_v2/scripts/test_broad_extraction_test.py`.
- Run a report-local saved-artifact replay against the approved count-24
  `sample_results.json`; do not invoke PDF extraction.

## Hard Stops

- Do not run count-24, count-32, random sampling, broad extraction, broad
  backfill, full ticker-universe extraction, or production repair.
- Do not invoke `run_multipass_extraction` against PDFs.
- Do not start runtime services or require model/GPU services.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts,
  gold labels, schemas, runtime/model/GPU/service config, or production data.
- Do not write outside the allowed files.
- Do not mutate GitHub except to push this branch and open a PR for this
  bounded diff.
- Do not merge, rebase, force-push, close issues, edit issues, label issues, or
  comment on issues.
- Do not use PR #318.

## Validation

- Validate this task card.
- Claim/release registry safely.
- Run focused broad-run tests.
- Run `py_compile` for changed scripts and saved replay.
- Run the saved-artifact replay and validate its JSON.
- Run `check-diff`, `check-report-artifacts`, and `git diff --check`.
- Push this branch and open a PR only after the focused validation remains
  clean.
