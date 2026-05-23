# Strategy Lab Mocked Adapter Contract v1

Status: design-only mock contract.

This document defines the future Tenn-owned sidecar adapter boundary for QuantDinger-style research tools. It does not implement a client, call a service, start QuantDinger, start MCP, issue a token, add dependencies, create an artifact store, or write Tenn stores.

## Boundary

- Tenn is the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator.
- Sidecar output may become a Strategy Lab artifact only after Tenn-owned policy, schema, quarantine, and review gates.
- Sidecar output is never canonical financial truth.
- All sidecar-derived artifacts default to `review_status=PENDING_REVIEW`.
- Tenn code owns tool execution policy, schema validation, permissions, audit logging, raw-output quarantine, and review boundaries.
- A local llama/router may propose an approved tool intent, but Tenn code executes and gates all calls.
- Codex remains a dev/audit agent only, not the runtime path.

## Components

### StrategyLabSidecarClient

Design role: a future Tenn-owned wrapper around one replaceable external sidecar transport.

Responsibilities:

- Accept a Tenn-built `ToolCallRequest`.
- Submit only operations allowed by `StrategyLabToolPolicy`.
- Attach audit context, idempotency keys, timeout settings, and rate-limit metadata.
- Return a `ToolCallResult` envelope.
- Never expose broker, exchange, paper-order, live-order, quick-trade, kill-switch, token-admin, or credential setup surfaces.
- Never write Tenn DB, Qdrant, news, memory, financial-truth, parser, extraction, gold-label, or source-registry state.

Non-responsibilities:

- No artifact persistence.
- No direct Strategy Lab review decision.
- No Cockpit UI/backend integration.
- No direct llama/router execution.
- No token issuance.

### StrategyLabToolPolicy

Design role: the Tenn-owned policy gate for all sidecar operations.

Responsibilities:

- Classify requested operations as `allowed_mock_only`, `default_hold`, or `blocked`.
- Reject forbidden trading, credential, admin, Tenn-store, parser/gold-label, source-registry, runtime, or Cockpit surfaces.
- Require `production_data_access=false`, `execution_allowed=false`, and `paper_live_scope=none`.
- Require mock scope, bounded input fields, audit fields, rate-limit expectations, and human-review rules.
- Return a `PolicyDecision` before any future sidecar call.

### StrategyLabArtifactAdapter

Design role: normalize accepted mock/future sidecar results into Phase 2 Strategy Lab artifact envelopes.

Responsibilities:

- Validate a raw result against operation-specific shape requirements.
- Map only eligible output into Phase 2 artifact types.
- Preserve mandatory flags:

```json
{
  "canonical_financial_truth": false,
  "production_data_access": false,
  "may_write_db": false,
  "may_write_qdrant": false,
  "may_write_memory": false,
  "may_write_financial_truth": false,
  "execution_allowed": false,
  "review_status": "PENDING_REVIEW"
}
```

- Require `source_of_idea`, `provenance`, `data_source`, `benchmark`, `limitations`, `raw_payload_ref`, `storage_policy`, `validation`, and `security_policy`.
- Emit `DATA_MISSING` explicitly rather than inferring provider, benchmark, source, assumptions, limitations, sample size, or raw hash.
- Quarantine invalid output instead of normalizing it into a valid artifact.

### MarketDataResearchClient

Design role: a future narrow facade for read-only market context operations.

Allowed design scope:

- `list_capabilities`
- `read_market_snapshot`

Output is context only. It does not become canonical price history, market truth, or source-backed claim verification. It may be referenced as `external_tool_context` in later artifacts, with provider gaps marked `DATA_MISSING` or `INFERRED`.

### BacktestResearchClient

Design role: a future narrow facade for bounded backtest submission and polling.

Allowed design scope:

- `submit_backtest`
- `get_backtest_result` / `get_job`

Eligible artifact type:

- `backtest_run`

Required boundary:

- Historical/simulated result only.
- No paper/live orders.
- No workspace strategy creation/update/run against a live workspace.
- No quick-trade or kill-switch operations.
- No broker/exchange credentials.

### RegimeResearchClient

Design role: a future narrow facade for regime classification context.

Allowed design scope:

- `regime_detect`

Eligible artifact type:

- `regime_breakdown`

Required boundary:

- Context only.
- Provider, segment times, candle counts, and sample sizes remain explicit `DATA_MISSING` if absent.
- Strategy family suggestions are external context, not Tenn recommendations or execution instructions.

## Envelope Types

### ToolCallRequest

Required fields:

- `request_id`: stable Tenn request id.
- `job_id`: Tenn job/task id.
- `requested_by`: `human`, `Tenn`, or future approved service id.
- `operation`: one allowlisted operation string.
- `mock_scope`: `phase3a_design_only`.
- `production_data_access`: must be `false`.
- `execution_allowed`: must be `false`.
- `paper_live_scope`: must be `none`.
- `input`: operation-specific input object.
- `source_of_idea`: Tenn-owned origin metadata.
- `policy_context`: lane, tenant, allowed markets, allowed artifact types, and forbidden surfaces.
- `audit_context`: trace id, timestamp, repo/task-card evidence, and policy version.

### PolicyDecision

Required fields:

- `decision`: `allow_mock_only`, `default_hold`, or `deny`.
- `operation`.
- `reason_codes`.
- `required_scope`.
- `forbidden_scope_detected`.
- `human_review_required`.
- `rate_limit`.
- `data_policy`.
- `artifact_policy`.
- `audit_log_fields`.

### ToolCallResult

Required fields:

- `request_id`.
- `operation`.
- `policy_decision`.
- `status`: `succeeded`, `accepted`, `running`, `failed`, `policy_denied`, `schema_invalid`, `sidecar_unavailable`, `data_missing`, or `quarantined`.
- `raw_payload_ref`.
- `result`.
- `artifact_mapping`.
- `quarantine`.
- `audit_log`.

### RawPayloadRef

Design-only fields:

- `storage_state`: `mock_ref_only`, `future_quarantine_store`, or `DATA_MISSING`.
- `path`: report-local or future quarantine path.
- `sha256`: explicit hash or `DATA_MISSING`.
- `source_report_path`.
- `redaction_status`.
- `quarantine_status`.

Phase 3A does not implement raw payload storage. Mock refs point only to design fixture paths.

### QuarantineResult

Required fields:

- `quarantined`: boolean.
- `reason_codes`.
- `raw_payload_ref`.
- `artifact_emitted`: boolean.
- `review_status`: `QUARANTINED_RAW_OUTPUT`, `FAILED_SCHEMA_VALIDATION`, `NEEDS_MORE_EVIDENCE`, or `PENDING_REVIEW`.
- `required_follow_up`.

### StrategyLabArtifact Mapping

Eligible mappings:

- `backtest_run`: from completed backtest job with benchmark/data gaps made explicit.
- `regime_breakdown`: from completed regime detect result with provider/sample/segment gaps made explicit.
- `parameter_sweep`: default hold until structured tuning result shape and compute caps are proven.
- `risk_report`: provisional/context only if derived from backtest risk metrics and clearly limited.
- `strategy_idea`: Tenn/human-origin only; QuantDinger must not decide research truth.
- `human_review_decision`: Tenn-owned only; sidecars must not emit it.

Ineligible mappings:

- Paper/live execution artifacts.
- Broker/exchange credential artifacts.
- Quick-trade, bot activation, kill-switch, token-admin, source-registry, Tenn-store, parser/extraction/gold-label, or Cockpit/runtime artifacts.
