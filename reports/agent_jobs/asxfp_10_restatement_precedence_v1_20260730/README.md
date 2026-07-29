# ASXFP Ticket 10 closeout

## Verdict

`REVIEW_READY`

The reviewed delta adds explicit, immutable amendment/restatement
supersessions and does not infer precedence from publication or arrival order.

## Pinned authority

- Base commit verified:
  `ba0688af97cdcaaf9cf21a0dddc2c1ba5aca2a33`
- Base tree verified:
  `4ec31edc8a2b43dd6d700fc4626acbc42d9cbc6b`
- Ticket SHA-256 verified:
  `c025e1d2e05a89e8e8c99577e6479283c8377fc632fc308b3b7634938873e9a0`

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
  one immutable evidence-bearing supersession edge per superseded observation.
- Staging accepts only `amendment` or `restatement`, requires an explicit source
  quote containing the matching marker, requires the quoted evidence to name
  the superseded source document, resolves exactly one predecessor, and checks
  the complete financial identity.
- Staging is integrated into the existing observation write function and does
  not commit; caller transaction ownership remains unchanged.
- Both legacy overlay reads and quarter/YTD additive reads exclude only
  superseded observations whose stored edge and evidence revalidate.
- `/financials/history` exposes active and superseded observations, immutable
  observation provenance, successor identity, relationship type, and
  supersession evidence.
- Focused fake tests cover migration/model consistency, explicit restated
  preference, rejection of ordinary or mismatched evidence, no service commit,
  provenance-bearing history, and proof that a later ordinary observation
  restores conflict abstention rather than replacing active truth.

## Validation

- `sha256sum <Ticket 10 authority>` — passed; exact requested digest.
- `git rev-parse HEAD` and `git rev-parse HEAD^{tree}` — passed; exact requested
  base and tree.
- `python3 scripts/agent_job_contract.py validate
  docs/agent_tasks/asxfp_10_restatement_precedence_v1_20260730.md` — passed
  with no issues; one expected legacy-v1 advisory.
- `python3 -m py_compile` on the changed Python source, migration, route, and
  focused test file — passed.
- Direct AST parse of the same five Python files — passed.
- `git diff --check` — passed.
- Focused fake-only financial-observation suite — `66 passed, 1 warning`.
- Ruff on all changed Python — passed.

## Prohibited-action compliance

No PDFs, protected corpus, metadata corpus, or diagnostic corpus were accessed.
No extraction, OCR, model, evaluation, service, database, migration, queue,
GPU, deployment, activation, runtime, or production write was run. No commit,
push, publish, PR action, merge, or external-service access occurred.

## Residual risks

- The migration was statically inspected and compiled but deliberately not
  executed against a database.
- The upstream producer must emit the new explicit
  `observation_supersessions` payload; absent or malformed evidence safely
  preserves conflict abstention.
