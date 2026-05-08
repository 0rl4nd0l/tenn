---
job_id: metric_extraction_runtime_contract_reconciliation_v1
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md
  - reports/agent_jobs/metric_extraction_runtime_contract_reconciliation_v1/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/metric_extraction_runtime_contract_reconciliation_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit whether Tenn intentionally retired the old strict extraction runtime on `:8002`, and define the current valid runtime contract for strict Docling metric extraction evaluation.

Do not restore `:8002` unless repo docs/scripts clearly prove it is still required.

# Lanes

Primary lane: Evaluation

Supporting lanes:
- Financial Truth
- Provenance

# Mode

AUDIT ONLY

# Hard boundaries

Do not edit:
- extraction logic
- extraction prompts
- parser routing
- evaluator logic
- gold labels
- canonical writes
- runtime config
- databases
- Qdrant
- source PDFs

Do not run a canonical accuracy eval until the valid runtime contract is confirmed.

# Required audit questions

1. Was `:8002` intentionally deprecated/canned?
2. What commit/doc/task/report made that decision, if any?
3. What runtime is now the intended strict extraction/eval runtime?
4. Does current extraction resolving to `:8001` represent intended architecture or accidental regression?
5. If `:8001` is intended, how does Tenn isolate strict extraction eval from shared chat/router load, prompt cache, fallback, and degraded-runtime contamination?
6. What env vars/scripts control extraction runtime selection? Check `EXTRACTION_LLAMACPP_URL` and related config.
7. Which existing eval commands are valid at current `HEAD`?
8. What baseline should replace the old `:8002 strict Docling` wording?
9. What must be proven before rerunning `canonical_core`?

# Required output

Write:
- `reports/agent_jobs/metric_extraction_runtime_contract_reconciliation_v1/README.md`

The README must include:
- Confirmed facts
- Inferred facts
- DATA_MISSING
- Relevant commits/docs/scripts inspected
- Current runtime contract
- Whether `:8002` is deprecated, broken, or unknown
- Whether `:8001` is safe for strict canonical eval
- Required guardrails before accuracy claims
- Recommended next Codex task

# Validation

Run:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- read-only searches, git history inspection, and static script/config inspection needed to answer the audit
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- `git status --short --untracked-files=all`

# Final report

Include:
- Files changed
- Files inspected
- Lane
- Execution mode
- Collision risk
- Validation run
- Validation result
- Files intentionally not touched
- Remaining blockers
- Next safe step
- Registry release status
