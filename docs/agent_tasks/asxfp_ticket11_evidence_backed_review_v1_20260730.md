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
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/README.md
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
docs_impact: TASK_CARD_REPORT_AND_CANONICAL_API_INVENTORY
docs_checked:
  - docs/extraction/financial_observation_contract.md
docs_changed:
  - docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/README.md
  - reports/agent_jobs/asxfp_ticket11_evidence_backed_review_v1_20260730/README.md
docs_followup: NONE
reason: "Ticket 11 adds an additive review queue without changing extraction guidance or the trusted-observation projection contract."
---

# ASXFP Ticket 11 evidence-backed review

## Authority

- Ticket 11 bounded CI-repair base:
  `7740cac802a3bab071a1815a6090d5672369883c`.
- Ticket 11 bounded CI-repair tree:
  `ff005d3f9433bb960352b2df29b894c25327fe35`.
- Current fresh exact-head rejection-repair base:
  `136c889ec7cce81d6c02d31717f0449693eefd9b`.
- Current fresh exact-head rejection-repair tree:
  `3f898a3867fdb2185521e3306d34f45a41f40d03`.
- Fresh exact-head rejection-repair base:
  `c958a7e77da1b782d58edb5c3531ab93a45e0fcd`.
- Fresh exact-head rejection-repair tree:
  `90e078fe3cc94351ae9e7a84f7656c655193eb1c`.
- Exact-head lifecycle repair base:
  `33327e0a44833d270b6a02324abc1815d27f3adb`.
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

This exact-head repair also requires every decision to persist a non-empty
decision actor, automatic UTC timestamp, and non-empty machine-readable
decision reason codes. An optional note remains supplemental. Approval
provenance keeps this decision audit separate from candidate review identity;
rejection remains non-promoting. The two review endpoints are added to the
repository's canonical API inventories.

The fresh rejection repair routes valid explicit, scoped abstain/quarantine
outcomes even when `field_provenance` is absent and evaluates every mapping in
`period_observations` at the single production staging seam. Unscoped or
malformed triggers remain ignored fail-closed. PostgreSQL enforces the decision
lifecycle plus a non-empty JSONB array of non-blank string reason codes; the
service separately validates normalized uniqueness before persistence because
the migration does not claim database-enforced array-element uniqueness.

The current rejection repair applies one fail-closed trust predicate to both
legacy profile upsert and accepted-observation promotion. Scoped explicit
abstain/quarantine values remain review candidates but cannot project;
malformed, unknown, or unscoped explicit trust metadata cannot project and
does not cause an outcome to be invented. Approval now proves persistence with
the exact inserted observation identity before changing review state. An
identity conflict fails deterministically, leaves the review pending, and is
rolled back by the decision endpoint.

The bounded CI repair keeps the migration's PostgreSQL JSONB column and
lifecycle constraint unchanged while declaring the ORM column as generic JSON
with a PostgreSQL JSONB variant, allowing SQLite test-schema compilation
without claiming SQLite enforcement of PostgreSQL-only JSONB predicates. The
ORM emits the lifecycle constraint only for PostgreSQL, matching its JSONB
functions; the migration keeps the production constraint unchanged. At the
production staging boundary, mutable extraction dictionaries are enriched in
place so both projection sinks receive the pre-existing caller payload
identity. Generic mappings are copied before enrichment. Enrichment still
occurs once and the same enriched staging payload reaches both sinks.

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

Current repair validation attempted: focused fake-only pytest, Python compile,
changed-file/allowlist inspection, and `git diff --check`. Runtime, database,
migration, extraction, OCR, model, queue, GPU, service, network, and protected
data validation remain prohibited.

Bounded CI-repair validation is recorded in the closeout report. The offline
interpreter has no pytest, SQLAlchemy, or Ruff installation, so executable
focused tests and ORM dialect compilation could not be run locally; no
dependency installation was attempted.
