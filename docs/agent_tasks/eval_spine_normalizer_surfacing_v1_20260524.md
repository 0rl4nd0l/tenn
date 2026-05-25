---
job_id: eval_spine_normalizer_surfacing_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md
  - reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524/README.md
  - reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524/status.json
  - reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524/validation.json
  - reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #50 by validating the existing Eval Spine normalizer safe-extension
and usage-follow-up artifact family into the issue-exact report path.

# Scope

Use current repo evidence and existing report artifacts to classify #50 as an
audit/safe-extension acceptance closeout. Do not claim Cockpit/runtime display
integration beyond current report-local/offline artifacts.

# Hard Boundaries

- Do not modify extraction logic, parser routing, prompts, gold labels,
  canonical truth, source PDFs, DB/Qdrant/news/memory stores, production data,
  Cockpit runtime surfaces, or services.
- Do not generate new extracted-payload accuracy claims.
- Mutate only this task card and listed issue-exact report artifacts.

# Required Outputs

- `reports/agent_jobs/eval_spine_normalizer_surfacing_v1_20260524/README.md`
- Current validation status.
- References to the existing normalizer implementation, usage follow-up sample
  artifacts, profile separation, and remaining display gaps.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
current branch/HEAD/status evidence, artifact presence checks, normalizer output
checks, `git diff --check`, and task-card check-diff.
