---
job_id: appendix4c_deterministic_sidecar_parser_prototype_v1
lane: Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/appendix4c_deterministic_sidecar_parser_prototype_v1.md
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/README.md
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/status.json
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/validation.json
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/parser_readiness_map.json
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/fixture_gate_proposal.json
  - reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #57 by running the issue-exact Appendix 4C deterministic sidecar
parser audit/design task. Bound the Appendix 4C scope, document deterministic
assumptions, propose isolated fixture/gate promotion criteria, and recommend the
next child prototype task if implementation becomes safe.

# Scope

Write only this task card and the listed report artifacts. Do not prototype code
in this pass because the lane is Financial Truth and the current branch has an
unrelated active registry job.

# Hard Boundaries

- Do not change production parser routing, Docling config, extraction prompts,
  canonical truth, source PDFs, DB/Qdrant/news/memory stores, production data,
  Cockpit runtime, model/runtime/service config, or gold labels.
- Do not infer revenue, NPAT, net debt, or income-statement blocks from Appendix
  4C cash-flow forms.
- Preserve candidate-only and canonical-write-false behavior until evaluation
  gates are explicit and approved.

# Required Outputs

- `reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/README.md`
- `status.json`
- `parser_readiness_map.json`
- `fixture_gate_proposal.json`
- `diff-check.json`
- Next child task recommendation.

# Validation

Run and report task-card validate, registry list-active, check-overlap, claim,
JSON validation, artifact evidence checks, `git diff --check`, task-card
check-diff, registry release, and final registry state.
