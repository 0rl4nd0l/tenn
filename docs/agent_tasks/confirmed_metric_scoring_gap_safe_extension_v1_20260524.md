---
job_id: confirmed_metric_scoring_gap_safe_extension_v1_20260524
title: Confirmed Metric Scoring Gap Safe Extension v1
owner: Codex
lane: Evaluation
primary_lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524
allowed_files:
  - docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md
  - financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/README.md
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/status.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/confirmed_metric_scoring_gap_report.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/validation.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/diff-check.json
allow_audit_code_changes: true
---

# Confirmed Metric Scoring Gap Safe Extension v1

Produce or normalize a confirmed metric coverage scoring-gap artifact from
current repo evidence now that source-PDF route resolution has been audited for
confirmed metric fixture source groups and scorecard-scored-ready rows.

## Scope

- Prove current repo path, branch, HEAD, dirty state, worktrees, registry state,
  task-card tooling, and overlap state before implementation.
- Preserve `canonical_core`, `expanded_required`, and
  `confirmed_metric_coverage` profile separation.
- Keep `confirmed_metric_coverage` denominators separate and use only eligible
  `CONFIRMED_SOURCE_EVIDENCED` / scorecard-scored-ready rows for the scoring-gap
  artifact.
- Preserve candidate and ambiguous exclusions unless a separate reviewed-label
  task promotes them later.
- Emit explicit `DATA_MISSING` for unavailable extracted-payload scoring,
  generated extraction_eval artifacts, graphify artifacts, or live HTTP
  source-route proof.

## Required Artifacts

- `README.md`
- `status.json`
- `confirmed_metric_scoring_gap_report.json`
- `validation.json`
- `diff-check.json`

## Boundaries

- Do not write canonical financial truth.
- Do not mutate DB, Qdrant, SQLite, Postgres, news stores, Tenn memory, company
  memory, market memory, thesis memory, or production data.
- Do not copy, download, move, import, normalize, or regenerate source PDFs.
- Do not mutate fixture labels.
- Do not promote candidate rows.
- Do not promote ambiguous or derived rows.
- Do not weaken source-route allowlists.
- Do not edit parser routing, extraction routing, Docling config, extraction
  prompts, canonical truth, or source PDFs.
- Do not run production extraction, ingestion, backfill, reindex, or resync.
- Do not claim broad metric extraction accuracy.
- Do not combine `canonical_core`, `expanded_required`, and
  `confirmed_metric_coverage` denominators.
- Do not touch unrelated dirty files.

## Hard Stops

Stop and report only if:

- task-card validation fails;
- active registry shows unresolved high overlap with Evaluation, Financial
  Truth, Provenance, confirmed metric coverage, extraction scorecards, source
  routing, parser/extraction, canonical truth, or allowed files;
- source-route openability no longer resolves the confirmed fixture PDFs;
- scoring would require candidate or ambiguous label promotion;
- extracted-payload generation would require production extraction or
  production data access;
- any change would touch parser routing, canonical truth, memory stores,
  DB/Qdrant, source-route allowlists, or source PDF files;
- current extracted-payload artifacts are missing and no safe fixture/report-only
  scoring artifact can be produced from existing allowed fixtures;
- profile denominators cannot be kept separate;
- allowed files are insufficient and a revised task card is needed;
- validation shows an uncontainable regression.
