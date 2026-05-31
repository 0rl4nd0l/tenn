---
job_id: extraction_synced_eval_verification_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_synced_eval_verification_v1_20260531.md
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/README.md
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/status.json
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/validation.json
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_synced_eval_verification_v1_20260531
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Synced Eval Verification

## Objective

Preserve current-turn evidence that the isolated extraction branch is based on
`origin/migration/clean-runtime-baseline-reconstruct-v1` after PR #129 and that
the local real-gold/evaluation guardrail lane passes with the metric ontology
gate slice on top.

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

- Target system layer: Evaluation reporting around metric extraction.
- Relevant contract rules: backend remains authoritative for canonical
  financial truth; metric extraction must extract explicit values only; report
  artifacts must not authorize writes.
- What must not change: runtime services, extraction prompts, parser routing,
  source PDFs, database schema, persisted financial rows, Qdrant, Cockpit UI,
  GitHub PR state, and canonical write permission.
- Why safe: this job only preserves validation evidence from local tests on an
  isolated branch.
- GPU process check required: no; no llama-server/backend process is spawned or
  required.

## Validation

- Confirm branch and relation to `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Run focused real-gold/scorecard/ontology/pre-canary/capability pytest.
- Run broader extraction evaluation lane pytest.
- Validate JSON report artifacts.
- Run raw binary/database artifact scan.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Release registry claim.

## Forbidden

- Backend, worker, llama, Docker, GPU, canary, runtime extraction, backfill, DB,
  Qdrant, source-PDF, parser, prompt, schema, Cockpit UI, GitHub, or canonical
  truth mutation.
- Treating local test evidence as full extraction graduation or canary success.
