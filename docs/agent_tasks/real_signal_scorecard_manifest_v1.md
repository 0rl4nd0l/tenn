---
job_id: real_signal_scorecard_manifest_v1
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/real_signal_scorecard_manifest_v1.md
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/README.md
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/status.json
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/validation.json
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/manifest.json
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/scorecards.json
  - reports/agent_jobs/real_signal_scorecard_manifest_v1/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/real_signal_scorecard_manifest_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Close GitHub #70 by creating a report-local Real Signal scorecard manifest slice
that encodes `real_signal_readiness_v1` rows from existing metadata and the #54
audit report. This is a safe extension to the report/artifact plane only.

# Scope

Write only the task card and issue-exact report artifacts listed above. Do not
add product code, runtime behavior, Cockpit UI, backend route behavior, parser
or extraction logic, or data-store writes.

# Hard Boundaries

- Do not mutate canonical financial truth, extraction routing, parser routing,
  extraction prompts, gold labels, source-label semantics, production data,
  DB/Qdrant/news/memory stores, model/runtime/service config, or Cockpit
  product surfaces.
- Do not derive `claim_verified` from model confidence, retrieval score, memory
  signal confidence, snippet-only context, source-ready news, or
  `unknown_unclassified` labels.
- Preserve DATA_MISSING for absent canonical rows, generated extracted payloads,
  runtime evidence, source evidence, or provenance evidence.

# Required Outputs

- `reports/agent_jobs/real_signal_scorecard_manifest_v1/README.md`
- `manifest.json`
- `scorecards.json`
- `status.json`
- `validation.json`
- `diff-check.json`

# Validation

Run and report task-card validate, registry list-active, check-overlap, claim,
JSON validation, artifact content checks for `scorecard_profile:
real_signal_readiness_v1`, `git diff --check`, task-card check-diff, registry
release, and final registry list-active.
