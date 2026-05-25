---
job_id: strategy_lab_quantdinger_regime_detect_fix_v1_20260524
title: Strategy Lab QuantDinger regime detect guard fix
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_regime_detect_fix_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/evidence.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/upstream_quantdinger_regime_guard_fix.patch
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/reproduction_before.txt
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/regression_after.txt
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_fix_v1_20260524/cleanup_proof.json
---

# Strategy Lab QuantDinger Regime Detect Guard Fix v1

## Objective

Implement and validate the narrow upstream-safe QuantDinger regime-detection
guard fix proven by the May 24 failure audit.

Use
`reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/`
as the authoritative evidence source.

## Scope

Apply the minimal safe upstream QuantDinger fix in an isolated temporary
sandbox only:

- either reject or skip segments with fewer than 30 candles before feature
  extraction
- or safely guard `_extract_features()` against fewer than 30 rows

Preserve the resulting upstream diff as a report artifact. Do not change Tenn
product/runtime behavior.

## Required Regression Coverage

- 20-row segments do not crash.
- 29-row segments do not crash.
- 30-row segments work.
- 50-row, 55-row, and 80-row windows continue working.

## Allowed Actions

- Read Tenn task cards, Strategy Lab reports, Strategy Lab docs, and tests.
- Create this task card and the report artifacts listed in `allowed_files`.
- Clone or copy QuantDinger into an isolated temporary sandbox for
  source-level reproduction and tests.
- Apply only the narrow regime-detection guard and regression tests inside the
  temporary upstream sandbox.
- Run source-level tests with synthetic OHLCV data.
- Run read-only validation commands against Tenn metadata and git state.

## Forbidden

- No live trading.
- No paper order placement.
- No broker credentials.
- No token storage.
- No Tenn DB, Qdrant, news, memory, or canonical-truth writes.
- No Strategy Lab UI/status mutation.
- No `current_sidecar_available=true`.
- No transport integration.
- No Tenn parser, routing, runtime, model-config, or product-code edits.

## Hard Stops

Stop before implementation if:

- task-card validation fails
- registry overlap is unsafe
- unresolved HIGH collision risk touches contested Tenn surfaces
- reproduction or validation would require credentials, token storage, paper
  orders, live trading, or Tenn store writes
- runtime validation cannot remain loopback-only, read-only, zero-order, and
  fully cleaned up

## Required Output

The final report must include:

- exact fix
- why it is safe
- exact reproduction before fix
- regression evidence after fix
- JSON validation
- `git diff --check`
- cleanup proof if a runtime or temporary sandbox was used
- whether clean re-probe is now justified
- whether `current_sidecar_available` remains false
- save recommendation
