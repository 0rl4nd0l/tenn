---
job_id: gold_metric_coverage_audit_v1_20260519
lane: Evaluation
supporting_lane: Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/README.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/corpus_inventory.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/scorecard_proposal.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/diff-check.json
approval_required: false
timeout_seconds: 21600
output_dir: reports/agent_jobs/gold_metric_coverage_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
allow_audit_code_changes: true
---

# Gold Metric Coverage Audit v1

Audit-only Evaluation task to inventory Tenn extraction-evaluation corpora, scorecards, gold labels, and reporting language so canonical no-regression scoring is not overstated as broad production extraction coverage.

## Scope

- Inspect existing repo evidence, fixtures, scorecards, evaluation scripts, gold labels, reports, docs, and prior validation artifacts.
- Separate `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` scorecard purposes.
- Write report artifacts only under `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/`.

## Hard Boundaries

- Do not run extraction jobs or live Docling extraction.
- Do not edit parser logic, prompts, gold labels, evaluator/scorer code, canonical writes, databases, Qdrant, memory, runtime, model, or GPU configuration.
- Do not start, stop, or restart services.
- Do not commit, stash, clean, or absorb unrelated worktree dirt.
