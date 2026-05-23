# Offline Implementation Plan

This is a future-work plan only. It does not implement code, transport, runtime
integration, artifact storage, or trading behavior.

## Tenn-Owned Client Boundary

Future implementation should define a Tenn-owned `StrategyLabSidecarClient`
boundary only after consolidation is resolved.

Required design properties:

- Tenn owns request construction, permission checks, schema validation, audit
  records, quarantine decisions, artifact emission decisions, and review gates.
- QuantDinger remains an external replaceable read/backtest sidecar/comparator.
- Sidecar responses are context or pre-envelope evidence only.
- The sidecar cannot write Tenn stores, approve artifacts, promote financial
  truth, mutate portfolios, create orders, issue tokens, or change runtime
  configuration.
- Codex remains a dev/test/review/planning agent, not a runtime execution path.

## Policy Before Dispatch

Every future sidecar call must pass a Tenn policy gate before dispatch.

The gate must evaluate:

- requested operation;
- lane and task-card authorization;
- production data access flag;
- allowed markets and symbols;
- allowed artifact types;
- forbidden surfaces;
- expected raw-output handling;
- idempotency key and audit context;
- timeout and rate-limit budget.

Policy decisions should be explicit:

- `allow_mock_only`
- `allow_offline_fixture_only`
- `default_hold`
- `deny`

No operation should dispatch when policy returns `default_hold` or `deny`.

## Mock-To-Real Transition Criteria

Real transport remains forbidden until a separate approved phase proves:

- consolidated Phase 2/3A/3B/3C baseline;
- production-code task card with exact allowed files;
- no-network production-module tests first;
- explicit credential/token plan that does not issue tokens during planning;
- timeout and retry budgets;
- rate limits per operation;
- raw-output quarantine location;
- schema validation and failure behavior;
- sidecar unavailable behavior;
- audit log schema;
- human review workflow;
- disabled-by-default feature flag.

The first real-sidecar smoke, if ever approved, must be isolated and must not
write Tenn stores, production data, source registry, parser labels, or trading
configuration.

## Schema Validation Gate

Future implementation must validate at two boundaries:

1. sidecar transport response shape;
2. mapped `strategy_lab_artifact_v1` envelope shape.

Rules:

- `strategy_lab_artifact_v1` remains authoritative.
- `strategy_lab_sidecar_artifact_v1` remains pre-envelope only.
- helper output can only map into the authoritative envelope or remain
  quarantined / `DATA_MISSING`.
- all machine-generated sidecar artifacts default to `PENDING_REVIEW`.
- only `backtest_run` and `regime_breakdown` are evidence-backed today.
- `parameter_sweep`, broad `risk_report`, `factor_test`, and
  `portfolio_experiment` remain held as `DATA_MISSING`.

## Raw Payload Quarantine And Persistence Design Topics

No artifact store should be implemented in Phase 3E or the next consolidation
phase.

Future design must answer:

- local quarantine path and retention policy;
- redaction rules for credentials and forbidden fields;
- raw payload hashing rules;
- parse status and schema-failure status;
- link from raw payload to audit record;
- link from raw payload to pending-review artifact;
- human review state transitions;
- deletion/expiry rules for unsafe raw outputs;
- separation from canonical financial truth and production stores.

Until those topics are approved, raw payload storage remains
`future_quarantine_store` or `DATA_MISSING`, not a real store implementation.

## Artifact Emission

Future artifact emission must be local, review-gated, and `PENDING_REVIEW` only.

Emission must require:

- policy allowed the operation;
- raw payload is present or `DATA_MISSING` is explicit where allowed;
- schema validation passed;
- no credential, order, broker, exchange, token-admin, store-write, source
  registry, parser/gold-label, runtime, Cockpit, paper, live, bot, or kill-switch
  fields were present;
- provenance and limitations are visible;
- benchmark/provider/hash gaps are explicit.

Artifact emission is not a store write and not a financial-truth promotion.

## Audit Logging

Future audit records should include:

- request id;
- job id and task card id;
- operation;
- policy version;
- decision and reason codes;
- forbidden surfaces detected;
- input summary without secrets;
- raw payload reference or explicit `DATA_MISSING`;
- schema validation result;
- quarantine result;
- artifact emission decision;
- human review requirement;
- rate-limit bucket;
- timeout budget;
- sidecar availability status.

Audit logs must never include plaintext credentials or tokens.

## Rate Limits And Timeouts

Phase 3A/3C evidence provides planning-level expectations, not production
values.

Future implementation should use conservative disabled-by-default limits:

- capabilities and market snapshot: low read rate;
- submit backtest: lower submit rate;
- polling: bounded backoff and maximum poll count;
- regime detect: separate bounded rate;
- no retries for policy-denied, schema-invalid, or forbidden-surface results;
- explicit timeout failure state and no partial artifact unless raw output is
  complete and valid.

Numeric limits remain future design choices until separately approved.

## Sidecar Unavailable Behavior

Sidecar unavailable must be a normal failed planning state, not an exception path
that bypasses policy.

Required behavior:

- no artifact emission by default;
- no Tenn store write;
- no retry storm;
- explicit audit record;
- user-visible `DATA_MISSING` or unavailable status in Strategy Lab context;
- no fallback to production data or alternate runtime path unless separately
  approved.

## No-Store-Write Invariants

Future implementation must preserve hard false flags for:

- DB writes;
- Qdrant/vector writes;
- news writes;
- memory writes;
- financial-truth writes;
- parser/gold-label writes;
- source-registry writes;
- holdings/watchlist/thesis mutation.

Any future persistence task must be a separate task card and must keep pending
artifacts separate from canonical truth.

## No-Trading-Scope Invariants

Forbidden until separately approved:

- broker credentials;
- exchange keys;
- paper orders;
- live orders;
- order routes;
- bot activation;
- quick trades;
- kill-switch behavior;
- scheduled/autonomous execution loops.

Policy must deny or quarantine sidecar output that contains trading authority,
order intent, credential fields, or execution claims.

## Human Review Gates

Human review is required before:

- displaying sidecar output as more than pending evidence;
- saving any artifact beyond local report/quarantine context;
- changing review state away from `PENDING_REVIEW`;
- using helper output as part of an authoritative envelope;
- enabling any real sidecar path.

## Feature Flags

Future implementation should be disabled by default.

Required flag model:

- separate flag for production-module import;
- separate flag for mock/offline transport tests;
- separate flag for real sidecar smoke;
- no environment variable or flag may enable trading, store writes, or token
  issuance under Strategy Lab sidecar work.

## Test Plan Before Implementation

Before any implementation phase, require tests for:

- policy-before-dispatch;
- denied forbidden surfaces;
- default-held operations;
- schema-valid pending artifacts;
- schema-invalid quarantine;
- missing raw payload quarantine;
- `DATA_MISSING` propagation;
- sidecar unavailable;
- timeout;
- no forbidden imports;
- no store-write calls;
- no paper/live/order/bot/kill-switch paths;
- disabled-by-default feature flags.
