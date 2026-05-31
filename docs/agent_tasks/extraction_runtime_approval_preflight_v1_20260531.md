---
job_id: extraction_runtime_approval_preflight_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_runtime_approval_preflight_v1_20260531.md
  - docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/README.md
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/status.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/validation.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/runtime_preflight.json
  - docs/claude/STATE.md
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Runtime Approval Preflight

## Objective

Refresh the read-only runtime/canary preflight from the handoff and preserve a
draft approval-required task card for a future third-canary run. This job must
not start runtime services or submit documents.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-metric-ontology-gate-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- Intended files: this task card, a draft approval-required canary execution
  task card, report artifacts under this output directory, and
  `docs/claude/STATE.md`.
- Contested surfaces touched: none.
- Collision risk: LOW; isolated worktree, report-only audit, no runtime or
  data-store mutation.
- Decision: proceed after task-card validation, overlap check, and claim.

## Contract Check

- Target system layer: Evaluation reporting around runtime readiness.
- Relevant contract rules: backend remains authoritative; metric extraction
  must not infer or substitute financial facts; runtime/canary execution must
  be approval-gated and one-document-at-a-time.
- What must not change: backend/worker/llama process state, source PDFs,
  parser routing, prompts, schemas, DB/Qdrant, Cockpit UI, GitHub state,
  persisted financial rows, and canonical write authorization.
- Why safe: this job only runs read-only probes and writes report artifacts.
- GPU process check required: read-only only; no process is spawned or
  restarted.

## Validation

- Validate this task card.
- Check registry overlap and claim.
- Run read-only backend health, queue, GPU, GPU guard, and process probes.
- Validate the draft approval-required canary task card.
- Validate JSON report artifacts.
- Run raw binary/database artifact scan.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Release registry claim.

## Forbidden

- Backend, worker, llama, Docker, GPU service startup/reload/restart.
- `POST /api/process/document/{document_id}` or any other document submission.
- Canary execution, backfill, DB/Qdrant/source-PDF/canonical-truth mutation.
- Parser, prompt, schema, Cockpit UI, GitHub, or model/GPU config mutation.
