# ASXFP Ticket 09 delivery evidence

## Authority

- Base commit: `9db0cb9a58c0475447f5cde41242e99d0d8cdac2`
- Ticket authority SHA-256:
  `79c319878337c2f8c6b1782c2b734c7a8815d2ef2b9a01ab5405ab8887b0e077`
- Prior owner authorization: `3 /goal use codex x to complete the rest of the
  tickets`, issued before this clean delivery branch was created. Repository
  policy independently authorizes Tier 1 local commits and draft PR delivery.

## Delivered behavior

- Canonical observations admit only source evidence that is both consolidated
  and statutory.
- Adjusted, underlying, normalized, and pro-forma values use a separate,
  immutable disclosure lane with exact source labels and reconciliation
  evidence.
- Missing or contradictory accounting basis, scope, label, provenance, or
  reconciliation evidence abstains.
- Canonical source evidence rejects every adjusted, underlying, normalized,
  normalised, pro forma, and pro-forma spelling.
- Disclosure labels use term boundaries, so labels such as `unadjusted` cannot
  authenticate an adjusted basis.
- The Ticket 05 revenue-only compatibility alias strips result disclosures.
- Fake-only staging fixtures prove a disclosed adjusted value cannot replace a
  statutory canonical value.

## Validation

- Focused fake-only financial-observation suite: `62 passed, 1 warning`.
- Ruff on all changed Python: passed.
- Changed Python syntax compilation: passed.
- Task-card validation and allowlist diff check: passed, with only the existing
  legacy-v1 migration warning.
- `git diff --check`: passed.

Migration execution remains intentionally excluded by the task boundary.

## Closeout

Exact changed paths:

- `docs/agent_tasks/asxfp_ticket09_statutory_adjusted_separation_v1_20260730.md`
- `docs/extraction/financial_observation_contract.md`
- `financial-engine_v2/backend/app/alembic/versions/0013_financial_result_disclosures.py`
- `financial-engine_v2/backend/app/models/__init__.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/tests/test_financial_observations.py`
- `reports/agent_jobs/asxfp_ticket09_statutory_adjusted_separation_v1_20260730/README.md`

Residual risks:

- The migration is syntax- and model-reviewed but intentionally not executed;
  database proof requires separate Tier 2 approval.
- Fake-only tests prove staging behavior without claiming extraction or
  production-runtime proof.
- Protected PDFs and holdout metadata remain untouched, so this ticket makes
  no corpus-quality claim.

Local delivery verdict: `REVIEW_READY`. The working tree is confined to the
eight allowed paths above.

- Exact implementation commit:
  `725340e5c838d6b110db30cd44458c744a6da2ef`
- Exact implementation tree:
  `926251d12d4d545c282e6ebb6fab7c37293d7e7b`
- Git status immediately after the implementation commit: clean.
- This report-only follow-up records the implementation identity. The final
  review-head identity and clean status remain externally verifiable Git facts.

## Boundaries

No PDFs or protected corpus data were accessed. No extraction, OCR/model
execution, services, databases, migrations, queues, GPUs, deployment,
activation, production writes, publication, merge, or runtime actions were
performed.
