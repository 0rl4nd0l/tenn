# Decisions

## Scope

- Integrated JAY only.
- Parked DXC as `NO_FIX_PROVEN`.
- Kept WHC report-only / existing opt-in-openability proof; no broad WHC repair.

## JAY

The product change is acceptable because it is deterministic and source-bound:

- quarterly market-update context is required;
- the current-quarter row label must match the payload period;
- the column must be explicitly `Net Revenue`;
- only canonical `revenue` is emitted;
- existing validation gates still run.

## DXC

`Net operating income` is not accepted as canonical `ebit` for the DXC source row because finance costs are present separately and no explicit EBIT row was found.

## WHC

The exact WHC source proof supports only the existing opt-in openability path. It does not justify broad scale propagation changes.

## Docs Impact

`DOCS_NOT_REQUIRED`: this is a narrow extraction behavior change covered by task card, tests, and report artifacts. No durable operator command, workflow, schema, API, or data-model documentation changed.

## Model And Worker Routing

- task_tier: `critical`
- recommended_model: `high reasoning`
- actual_model: `Codex GPT-5`
- worker_model_allowed: `true`
- worker_decision_limit: workers supplied evidence only; orchestrator owned integration and PR readiness.
- escalation_needed: `false`
