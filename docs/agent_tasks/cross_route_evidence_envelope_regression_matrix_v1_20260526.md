---
job_id: cross_route_evidence_envelope_regression_matrix_v1_20260526
lane: Evaluation
supporting_lanes:
  - Provenance
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cross_route_evidence_envelope_regression_matrix_v1_20260526.md
  - reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526/README.md
  - reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526/evidence_envelope_matrix.json
  - reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526/status.json
  - reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526/validation.json
  - reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cross_route_evidence_envelope_regression_matrix_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: issue_comment_and_child_issue_creation
related_issue: 104
---

# Cross-Route Evidence Envelope Regression Matrix

## Objective

Produce an audit-only route-parity matrix for Cockpit evidence envelope
semantics across chat, persisted chat reload, news status, Home panels, Home
source drawer, and attached/source drawer surfaces.

## Scope

Allowed writes are limited to this task card and the report bundle under the
configured output directory. Source, test, runtime, UI, data, parser, prompt,
database, Qdrant, news, memory, model, GPU, and service files are read-only.

## Required Audit Coverage

- Expected evidence-envelope fields and allowed values.
- Backend support versus frontend visibility.
- At least these states: claim-verified, context-only, no-hit, degraded
  runtime, DATA_MISSING, unknown/unclassified, memory-context, local-news,
  external-web-context, and financial-truth.
- Saved/session reload preservation.
- Existing issue links for #83, #84, #87, and #95.
- `NO_FOLLOWUP` where current evidence proves a route is covered.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cross_route_evidence_envelope_regression_matrix_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cross_route_evidence_envelope_regression_matrix_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cross_route_evidence_envelope_regression_matrix_v1_20260526.md --repo-root .`
- Static/source-route inspection only.
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cross_route_evidence_envelope_regression_matrix_v1_20260526.md --repo-root .`
- Registry release before closeout.

## Hard Stops

- Duplicate tracker found.
- Required implementation would touch contested chat/source/Home/backend routes.
- Any required change would weaken source labels or relabel context/no-hit/
  degraded evidence as claim-verified.
- Product/runtime/data mutation becomes necessary.
