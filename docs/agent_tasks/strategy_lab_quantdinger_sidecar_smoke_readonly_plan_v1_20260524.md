---
job_id: strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524
lane: Reporting
owner: Codex
supporting_lanes:
  - Provenance
  - Evaluation
mutation_mode: audit_only
approval_required: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524/diff-check.json
---

# Strategy Lab QuantDinger Sidecar Smoke Read-Only Plan v1

## Objective

After explicit approval, perform one tiny non-mock QuantDinger sidecar smoke
from an isolated reporting lane and capture only availability/failure evidence.
This task card is a plan and approval gate. It does not authorize execution by
itself.

## Approval Gate

Do not run real QuantDinger transport, start services, issue tokens, use broker
credentials, call paper/live execution, or contact external endpoints until a
human explicitly approves this task and confirms the target sidecar endpoint.

## Intended Smoke Shape

- Input: one deterministic, non-production, public-data sample such as
  `market=Crypto`, `symbol=BTC/USDT`, `timeframe=1D`, and a very short date
  window.
- Scope: read-only capability or status probe first; one bounded backtest or
  regime probe only if the sidecar already supports read/backtest-only mode and
  the approval explicitly includes it.
- Output: report artifacts only under this task `output_dir`.
- Failure capture: record unavailable, authentication missing, timeout, schema
  mismatch, policy-denied, or endpoint-not-found states as `DATA_MISSING` or
  blocked evidence instead of retrying broadly.

## Forbidden

- No trading, broker, paper/live execution, token issuance without explicit
  approval, market orders, bot activation, or portfolio mutation.
- No Tenn DB, Qdrant, news, memory, canonical financial truth, artifact-store,
  promotion, parser, extraction, gold-label, runtime/model/GPU, dependency, or
  service changes.
- No production data access.
- No write-back to Strategy Lab artifacts, reports outside this task output,
  memory, stores, or canonical truth.
- No credential logging.

## Preconditions For A Later Approved Run

- Validate this task card.
- Registry `list-active` and `check-overlap` must be clean.
- Confirm the sidecar target endpoint, transport type, and auth mode from
  current repo evidence or explicit user-provided values.
- Confirm no sidecar/broker/trading tokens are required; if a token is required
  and was not explicitly approved for this exact smoke, stop with
  `DATA_MISSING`.
- Confirm the request cannot mutate portfolios, orders, bot state, paper state,
  live state, Tenn stores, or canonical financial truth.

## Validation For A Later Approved Run

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md --repo-root .`
- Record exact request metadata with secrets redacted.
- Parse response JSON if any.
- Assert no order, paper/live, broker, token, portfolio, Tenn store, or
  canonical financial truth write occurred.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md --repo-root .`

## Done Criteria

- A report says whether the sidecar is unavailable, blocked, policy-denied, or
  read-only responsive.
- Any response is labeled external sidecar evidence only, not canonical
  financial truth.
- Registry is released.
- No code, dependency, runtime, store, trading, paper/live, credential, or
  production-data changes occur.
