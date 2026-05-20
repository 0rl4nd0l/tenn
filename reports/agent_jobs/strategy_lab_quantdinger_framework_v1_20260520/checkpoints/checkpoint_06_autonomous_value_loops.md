# M6 - Autonomous Value Loop Framework

Autonomous here means "research automation that writes reviewable artifacts." It does not mean trading, broker setup, paper execution, live execution, production data mutation, or memory writes.

## Loop 1 - Watchlist Opportunity Scan

- Trigger: scheduled or manual watchlist scan.
- Inputs: watchlist tickers, existing Tenn analysis artifacts, recent local news context, optional read-only sidecar market data in future phases.
- Allowed tools: Tenn read-only context, watchlist artifact reads, future QuantDinger read/regime/backtest only when approved.
- Forbidden tools: credentials, trading, paper execution, live execution, memory write, financial truth write.
- Output artifact: `autonomous_opportunity_note`.
- Human review: required before surfacing outside Strategy Lab.
- Failure modes: stale watchlist, missing price data, no news hits, sidecar unavailable, over-broad ticker inference.
- Regression tests needed: no-trade assertion, no-memory-write assertion, source-label preservation, DATA_MISSING rendering.

## Loop 2 - Thesis-To-Strategy Tester

- Trigger: human selects thesis or Chat output and asks for a research test.
- Inputs: thesis text, ticker/universe, time window, benchmark, assumptions.
- Allowed tools: strategy idea artifact creation; future bounded backtest after approval.
- Forbidden tools: autonomous code execution outside sandbox, workspace writes before schema quarantine, any broker action.
- Output artifact: `strategy_idea`, then optional `backtest_run`.
- Human review: required before any backtest; required again after result.
- Failure modes: thesis too vague, missing benchmark, LLM-generated rule mismatch, lookahead bias.
- Regression tests needed: benchmark required, assumptions required, execution fields rejected, review state default pending.

## Loop 3 - Factor Hypothesis Generator

- Trigger: periodic Evaluation job or human prompt.
- Inputs: Tenn analysis module outputs, market/news context, watchlist, factor definition library.
- Allowed tools: read-only artifact analysis, future factor-test sandbox.
- Forbidden tools: production DB writes, Qdrant writes, financial truth reinterpretation, live trading.
- Output artifact: `factor_test` or `strategy_idea`.
- Human review: required before factor appears in UI recommendation surfaces.
- Failure modes: data snooping, small sample, survivorship bias, factor redundancy.
- Regression tests needed: sample-size warning, factor-correlation warning, no canonical truth label.

## Loop 4 - Strategy Drift Monitor

- Trigger: scheduled comparison of prior approved research artifacts against new data windows.
- Inputs: prior Strategy Lab artifacts, updated read-only price/news data, review decisions.
- Allowed tools: read-only artifact reads and future bounded backtest reruns.
- Forbidden tools: auto-rebalancing, broker execution, memory writes.
- Output artifact: `risk_report` or `regime_breakdown`.
- Human review: required for any "drift" conclusion to affect watchlist priority.
- Failure modes: changed data vendor, missing old raw outputs, benchmark drift, sidecar version drift.
- Regression tests needed: run/version comparison, result-not-comparable state, DATA_MISSING if prior artifact missing.

## Loop 5 - Portfolio Risk Sentinel

- Trigger: manual or scheduled review of local holdings or portfolio experiment artifacts.
- Inputs: user holdings marked `local_personal_data`, risk artifacts, price data, approved research context.
- Allowed tools: read-only holdings context, risk simulation artifact generation.
- Forbidden tools: order generation, rebalancing execution, broker integration, financial truth writes.
- Output artifact: `portfolio_experiment` or `risk_report`.
- Human review: required before any suggestion enters Chat/Watchlist.
- Failure modes: stale holdings, mixed currencies, missing prices, false precision.
- Regression tests needed: `local_personal_data` label, no source-backed financial-truth overclaim, mixed-currency warning.

## Loop 6 - Self-Improvement Backlog Generator

- Trigger: completed review queue, failed schemas, repeated DATA_MISSING, or rejected artifacts.
- Inputs: Strategy Lab artifacts, validation results, review decisions.
- Allowed tools: report inspection and future task-card outline generation.
- Forbidden tools: code edits, runtime changes, DB/Qdrant/memory writes, auto-PR creation unless separately authorized.
- Output artifact: future task-card outline.
- Human review: required before task card creation beyond allowed report bundle.
- Failure modes: noisy backlog, duplicates, stale assumptions, task scope creep.
- Regression tests needed: exact forbidden surfaces, allowed file boundaries, no implementation action.

## Cross-Loop Rules

- Every loop must produce a bounded artifact, not an action.
- Every loop must default to `PENDING_REVIEW`.
- Every loop must have hard blocks for paper/live execution.
- Every loop must use DATA_MISSING for missing evidence.
- Every loop must identify whether outputs touch Financial Truth, Memory, Query Orchestration, Reporting, Provenance, or Evaluation.
