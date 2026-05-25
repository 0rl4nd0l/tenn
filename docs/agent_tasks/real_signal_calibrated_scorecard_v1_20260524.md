---
job_id: real_signal_calibrated_scorecard_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/real_signal_calibrated_scorecard_v1_20260524.md
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/README.md
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/status.json
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/validation.json
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/scorecard_proposal.json
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/gap_register.json
  - reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #54 by running the issue-exact Real Signal calibrated scorecard
audit-first task. Locate and classify current heuristic, provenance, reporting,
and actionability surfaces that could be confused with a Real Signal score, then
produce a report-only calibrated scorecard proposal with explicit DATA_MISSING
handling.

# Scope

Use current repo and GitHub evidence only. This task may write the task card and
listed report artifacts. It may not implement product behavior, alter runtime
services, or claim Cockpit-visible remediation.

# Hard Boundaries

- Do not modify canonical financial truth, extraction routing, parser routing,
  extraction prompts, gold labels, source-label semantics, production data,
  DB/Qdrant/news/memory stores, model/runtime/service config, or unrelated dirty
  files.
- Do not weaken provenance labels or treat heuristic/model confidence as
  deterministic financial truth.
- Do not execute memory/news/data-store write paths while auditing signal
  surfaces.

# Required Outputs

- `reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/README.md`
- `status.json`
- `scorecard_proposal.json`
- `gap_register.json`
- `validation.json`
- Recommended child task if implementation is justified.

# Validation

Run and report task-card validate, registry list-active, check-overlap, claim,
current branch/HEAD/status evidence, artifact JSON validation, `git diff
--check`, task-card check-diff, and registry release.
