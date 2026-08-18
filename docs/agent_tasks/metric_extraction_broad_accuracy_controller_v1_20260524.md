---
job_id: metric_extraction_broad_accuracy_controller_v1_20260524
title: Metric Extraction Broad Accuracy Controller v1
owner: Codex
lane: Financial Truth
primary_lane: Financial Truth
supporting_lanes:
  - Evaluation
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 21600
output_dir: reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524
allowed_files:
  - docs/agent_tasks/metric_extraction_broad_accuracy_controller_v1_20260524.md
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/README.md
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/status.json
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/metric_extraction_coverage_map.json
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/metric_extraction_gap_register.json
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/safe_extension_candidates.json
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/no_regression_gate_plan.md
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/validation.json
  - reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/diff-check.json
allow_audit_code_changes: true
---

# Metric Extraction Broad Accuracy Controller v1

Audit and safely advance Tenn's broad financial metric extraction accuracy and
functionality without corrupting canonical truth, weakening provenance, or
claiming broad accuracy before scorecards prove it.

## Scope

- Prove current repo path, branch, HEAD, dirty state, worktrees, registry state,
  and active-job overlap before relying on this checkout.
- Audit current metric extraction coverage and failure modes across
  `canonical_core`, `expanded_required`, `confirmed_metric_coverage`, Appendix
  5B, Appendix 4C readiness, parser/layout, period/currency/unit/sign
  ambiguity, source binding, scorer/evaluator coverage, Cockpit verification,
  and no-regression gates.
- Write report-only artifacts under
  `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/`.
- Propose safe-extension child tasks only where current evidence supports a
  bounded low/medium-risk follow-up.

## Required Artifacts

- `README.md`
- `status.json`
- `metric_extraction_coverage_map.json`
- `metric_extraction_gap_register.json`
- `safe_extension_candidates.json`
- `no_regression_gate_plan.md`
- `validation.json`
- `diff-check.json`

## Boundaries

- Do not write canonical financial truth.
- Do not change production extraction routing, parser routing, Docling
  configuration, or extraction prompts.
- Do not mutate DB, Qdrant, SQLite, news stores, Tenn memory, company memory,
  market memory, thesis memory, or production data.
- Do not run ingestion, backfill, reindex, resync, extraction, parser, runtime,
  model, GPU, Docker, systemd, or cron jobs.
- Do not relax labels, scorecards, provenance requirements, gates, or source
  binding semantics.
- Do not claim broad metric extraction accuracy unless scorecards prove it.
- Do not touch unrelated dirty files.

## Hard Stops

Stop or remain report-only if:

- task-card validation fails;
- required current repo state remains `DATA_MISSING` after preflight;
- active registry or dirty files create unresolved high collision risk;
- allowed files cannot be bounded;
- canonical financial truth, parser routing, production extraction, Tenn memory,
  Qdrant, DB, news store, runtime binding, migration, or cleanup would need to
  change;
- production data access would be required;
- validation reveals an uncontainable regression.
