---
job_id: asxfp_ticket11_evidence_backed_review_v1_20260730
title: Route unresolved financial observations through evidence-backed review
lane: Financial Truth
supporting_lanes:
  - Provenance
owner: Codex
approval_required: true
approval_status: granted
approval_evidence: "Before this delivery branch existed, the owner requested: '3 /goal use codex x to complete the rest of the tickets'. Repository policy independently permits Tier 1 local commits and draft PR delivery."
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
task_tier: standard
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/asxfp_ticket11_evidence_backed_review_v1_20260730
closeout_scope: controller_local_commit
allowed_files:
  - docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md
  - financial-engine_v2/backend/app/alembic/versions/0015_financial_observation_reviews.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/models/__init__.py
  - financial-engine_v2/backend/app/models/financial_observations.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/financial_observations.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/tests/test_financial_observation_reviews.py
  - financial-engine_v2/backend/tests/test_financial_observations.py
  - reports/agent_jobs/asxfp_ticket11_evidence_backed_review_v1_20260730/README.md
docs_impact: TASK_CARD_AND_REPORT_ONLY
docs_checked:
  - docs/extraction/financial_observation_contract.md
docs_changed:
  - docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md
  - reports/agent_jobs/asxfp_ticket11_evidence_backed_review_v1_20260730/README.md
docs_followup: NONE
reason: "Ticket 11 adds an additive review queue without changing extraction guidance or the trusted-observation projection contract."
---

# ASXFP Ticket 11 evidence-backed review

## Authority

- Second repair base commit: `08420f349077158b8a537912d59e0f07d3b347bf`.
- Second repair base tree: `57b10a1addf6883faef5d14af4385ac95d8d62eb`.
- Parent before Ticket 11: `c57698a2e852d74d84dbb30402a0d654515d6a44`.
- Ticket 11 authority SHA-256:
  `e28516984ca7b020f028385908c383b1e3fcb2b41617e30f7561bff34bdebea8`.

## Scope

Add an observation-specific review queue with closed unresolved states,
machine-readable reason codes, complete location and financial-context evidence,
authenticated review reads and decisions, and a fail-closed approval path.
Preserve the existing automatic profile projection for trusted observations.

This bounded repair expands the original allowlist only to
`app/services/extraction_eval.py` and `app/services/pipeline.py`. The former
exposes the existing raw-payload provenance validator at the production
boundary; the latter invokes that enrichment immediately before observation
staging. Both are required because production staging otherwise receives raw
structured extraction output without the evaluation detail consumed by the
Ticket 11 adapter.

## Explicit allowlist

Only the paths in front matter `allowed_files` may change. Launcher-owned
untracked control files are out of scope and must remain untouched.

## Prohibited work

No PDFs, corpora, diagnostics, holdout data, extraction, OCR, models, services,
databases, migrations, queues, GPUs, deployments, activation, production
writes, network actions, pushes, PRs, or merges. This repair worker must not
commit. `controller_local_commit` explicitly authorizes only the Codex X
controller to create the final local delivery commit after worker validation;
it does not authorize this worker or any push, PR, or merge.

## Validation

Compile-only checks, focused fake-only tests when local dependencies are
available, changed-file static checks, and `git diff --check`.
