# ASXFP Ticket 10 closeout

## Verdict

`REVIEW_READY`

The rejected-head findings are repaired within the existing seven paths.
Validated supersession topology, rather than publication or arrival order,
now determines active precedence.

## Pinned authority

- Base commit verified:
  `ba0688af97cdcaaf9cf21a0dddc2c1ba5aca2a33`
- Base tree verified:
  `4ec31edc8a2b43dd6d700fc4626acbc42d9cbc6b`
- Ticket SHA-256 verified:
  `c025e1d2e05a89e8e8c99577e6479283c8377fc632fc308b3b7634938873e9a0`
- Rejected head verified:
  `d98a4d9543c8979d98c66f550d2da745bd3e521b`
- Rejected tree verified:
  `69aef37e7582c842a97efef7dc1aebe55b823043`

## Rejected review and repaired behavior

- Active selection previously removed only superseded nodes. An unrelated
  ordinary 110 therefore conflicted with the validated terminal restatement
  90. Active reads now select unsuperseded terminal nodes for identities with
  validated topology; legacy and quarter/YTD projections retain 90.
- Retry inserts previously passed only newly inserted observations into
  supersession staging. A deterministic observation that already existed
  after `ON CONFLICT DO NOTHING` was lost. Staging now resolves and passes that
  candidate while continuing to return only newly inserted observations.
- The ORM-generated superseding-observation index name differed from the
  migration. Both now use
  `ix_financial_observation_supersessions_superseding`, with focused proof of
  columns, foreign keys, constraints, index, and migration trigger DDL.
- Supersession immutability was previously a claim without persistence
  enforcement. The forward migration now installs a PostgreSQL trigger that
  rejects updates and deletes, covering relationship fields and JSON evidence.
- `/financials/history` previously exposed IDs, provenance, and evidence
  without authentication. It now uses the established
  `Depends(require_api_key)` guard. Route-level coverage proves configured-key
  rejection and authorized availability, and confirms `/financials` is
  registered before `/financials/history`.
- Exact-head review of `8d510c9734295bbf1811ee76704c995c91734b2f`
  found that history still labeled a suppressed later ordinary observation
  active. History now reuses the same validated topology-terminal selector as
  projections; focused coverage proves the restatement is active and the later
  ordinary observation remains queryable but inactive.

## Changed paths

- `docs/agent_tasks/asxfp_10_restatement_precedence_v1_20260730.md`
- `financial-engine_v2/backend/app/alembic/versions/0014_observation_supersessions.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/tests/test_financial_observations.py`
- `reports/agent_jobs/asxfp_10_restatement_precedence_v1_20260730/README.md`

Launcher-owned untracked control artifacts pre-existed the implementation,
were excluded from the task allowlist, and were not modified.

## Implementation evidence

- A forward-only migration and matching ORM model retain observations and add
  one persistence-enforced immutable evidence-bearing supersession edge per
  superseded observation.
- Staging accepts only `amendment` or `restatement`, requires an explicit source
  quote containing the matching marker, requires the quoted evidence to name
  the superseded source document, resolves exactly one predecessor, and checks
  the complete financial identity.
- Staging is integrated into the existing observation write function and does
  not commit; caller transaction ownership remains unchanged.
- Both legacy overlay reads and quarter/YTD additive reads prefer validated
  topology terminals and otherwise retain the existing conflict-abstention
  behavior.
- Authenticated `/financials/history` exposes active and superseded
  observations, immutable observation provenance, successor identity,
  relationship type, and supersession evidence, with activity derived from the
  same topology terminals as the active projections.
- Focused fake tests cover migration/model consistency, explicit restated
  preference, rejection of ordinary or mismatched evidence, no service commit,
  provenance-bearing history, idempotent retry, API-key enforcement, route
  order, and proof that later ordinary observations cannot displace terminal
  restatements in legacy or quarter/YTD reads.

## Validation

- `sha256sum <Ticket 10 authority>` — passed; exact requested digest.
- `git rev-parse HEAD` and `git rev-parse HEAD^{tree}` — passed; exact rejected
  head and tree.
- `python3 scripts/agent_job_contract.py validate
  docs/agent_tasks/asxfp_10_restatement_precedence_v1_20260730.md` — passed
  with no issues; one expected legacy-v1 advisory.
- `python3 -m py_compile` on the changed Python source, migration, route, and
  focused test file — passed.
- Direct AST parse of the same five Python files — passed.
- `git diff --check` — passed.
- Focused fake-only financial-observation suite in a disposable `uv`
  environment — `69 passed, 1 warning`.
- Ruff on all changed Python — passed.

## Prohibited-action compliance

No PDFs, protected corpus, metadata corpus, or diagnostic corpus were accessed.
No extraction, OCR, model, evaluation, service, database, migration, queue,
GPU, deployment, activation, runtime, or production write was run. No commit,
push, publish, PR action, merge, or external-service access occurred during
the bounded repair worker run; the controller may create the authorized local
repair commit after validation.

## Residual risks

- The migration was statically inspected and compiled but deliberately not
  executed against PostgreSQL, so trigger installation remains execution-time
  validation for the integration environment.
- The upstream producer must emit the new explicit
  `observation_supersessions` payload; absent or malformed evidence safely
  preserves conflict abstention.
