---
job_id: extraction_goal_proof_matrix_refresh_v3_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_goal_proof_matrix_refresh_v3_20260531.md
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/README.md
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/status.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/validation.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/diff-check.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/objective_matrix.json
  - docs/claude/STATE.md
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Goal Proof Matrix Refresh V3

## Objective

Refresh the 10-item metric extraction proof matrix using current branch,
runtime, registry, GitHub-read-only, and local validation evidence after the
metric ontology gate and runtime approval-preflight slices.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-metric-ontology-gate-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- Intended files: this task card, report artifacts under this output directory,
  and `docs/claude/STATE.md`.
- Contested surfaces touched: none.
- Collision risk: LOW; isolated worktree, report-only audit, no runtime or
  data-store mutation.
- Decision: proceed after validation, overlap check, and claim.

## Contract Check

- Target system layer: Evaluation reporting.
- Relevant contract rules: backend remains authoritative; metric extraction
  must extract explicit values only; report artifacts cannot authorize
  canonical writes.
- What must not change: runtime services, extraction prompts, parser routing,
  source PDFs, database schema, persisted financial rows, Qdrant, Cockpit UI,
  GitHub state, and canonical write permission.
- Why safe: this job reads evidence and writes report artifacts only.
- GPU process check required: read-only only; no process is spawned or
  restarted.

## Validation

- Validate this task card.
- Check registry overlap and claim.
- Refresh GitHub PR state read-only.
- Rerun focused extraction proof/eval tests as current-turn evidence.
- Reuse current read-only runtime probes.
- Validate JSON report artifacts.
- Run raw binary/database artifact scan.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Release registry claim.

## Forbidden

- Backend, worker, llama, Docker, GPU service startup/reload/restart.
- Canary execution or document submission.
- DB/Qdrant/source-PDF/canonical-truth mutation.
- Parser, prompt, schema, Cockpit UI, GitHub, or model/GPU config mutation.
