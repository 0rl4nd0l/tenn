---
job_id: confirmed_metric_source_pdf_resolution_audit_v1_20260524
title: Confirmed Metric Source PDF Resolution Audit v1
owner: Codex
lane: Evaluation
primary_lane: Evaluation
supporting_lanes:
  - Provenance
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524
allowed_files:
  - docs/agent_tasks/confirmed_metric_source_pdf_resolution_audit_v1_20260524.md
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/README.md
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/status.json
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/source_pdf_resolution_matrix.json
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/source_path_gap_register.json
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/next_task_recommendation.md
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/recommended_child_task_card.md
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/validation.json
  - reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/diff-check.json
allow_audit_code_changes: true
---

# Confirmed Metric Source PDF Resolution Audit v1

Audit confirmed metric coverage source PDF/path resolution from current repo
evidence and produce an explicit source-path/DATA_MISSING report without
copying PDFs, weakening allowlists, mutating fixture labels, or claiming broad
metric extraction accuracy.

## Scope

- Prove current repo path, branch, HEAD, dirty state, worktrees, registry state,
  task-card tooling, and overlap state before relying on this checkout.
- Inspect parent metric extraction audit artifacts, confirmed metric coverage
  fixtures/inventory, confirmed metric coverage review service/tests, source
  route/allowlist behavior, and existing report artifacts.
- Classify source evidence for confirmed metric coverage rows or source groups
  as openable local source, missing local source, path mismatch,
  allowlist-blocked, external-only, ambiguous source reference,
  source-unopenable, or DATA_MISSING.
- Decide whether confirmed metric scoring can proceed safely or must remain
  blocked by source evidence gaps.
- Recommend exactly one next safe task and draft a child task card only if
  justified.

## Required Artifacts

- `README.md`
- `status.json`
- `source_pdf_resolution_matrix.json`
- `source_path_gap_register.json`
- `next_task_recommendation.md`
- `recommended_child_task_card.md`
- `validation.json`
- `diff-check.json`

## Boundaries

- Do not copy, download, import, normalize, move, rename, or regenerate source
  PDFs.
- Do not mutate confirmed metric coverage fixture labels.
- Do not mark candidate, ambiguous, or source-missing rows as scored.
- Do not weaken source-route allowlists.
- Do not edit source-route code, parser code, Docling config, extraction
  prompts, extraction routing, canonical truth, or scoring rules.
- Do not run production extraction, ingestion, backfill, reindex, or resync.
- Do not mutate DB, Qdrant, SQLite, Postgres, news stores, Tenn memory,
  company memory, market memory, thesis memory, or production data.
- Do not claim broad metric extraction accuracy.
- Do not combine `canonical_core`, `expanded_required`, and
  `confirmed_metric_coverage` into one broad score.
- Do not touch unrelated dirty files.

## Hard Stops

Stop or remain report-only if:

- task-card validation fails;
- active registry shows unresolved high overlap with Evaluation, Provenance,
  confirmed metric coverage, source routing, parser/extraction, or financial
  truth surfaces;
- source PDF resolution would require copying/importing production PDFs;
- a fix would require source-route allowlist weakening, fixture-label mutation,
  parser routing, canonical truth writes, or production extraction;
- validation reveals disallowed diffs.
