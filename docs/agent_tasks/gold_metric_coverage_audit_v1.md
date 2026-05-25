---
job_id: gold_metric_coverage_audit_v1
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/gold_metric_coverage_audit_v1.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1/README.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1/status.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1/validation.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/gold_metric_coverage_audit_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #37 by validating the existing Gold Metric Coverage Audit v1
artifact family and writing the issue-exact report surface.

# Scope

Use current repo evidence plus existing dated audit artifacts to confirm the
separation between `canonical_core`, `expanded_required`, and
`confirmed_metric_coverage`.

# Hard Boundaries

- Do not run extraction jobs or live Docling extraction.
- Do not edit parser logic, prompts, gold labels, evaluator/scorer code,
  canonical writes, databases, Qdrant, memory, runtime, model, or GPU
  configuration.
- Do not start, stop, or restart services.
- Do not mutate product, backend, frontend, runtime, financial-truth, memory,
  data-store, source PDF, news, or extraction implementation files.
- Mutate only this task card and listed issue-exact report artifacts.

# Required Outputs

- `reports/agent_jobs/gold_metric_coverage_audit_v1/README.md`
- Current validation status.
- References to the existing corpus inventory, metric inventory, scorecard
  proposal, and current confirmed-metric scoring gap evidence.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
existing artifact JSON checks, current evidence references, `git diff --check`,
and task-card check-diff.
