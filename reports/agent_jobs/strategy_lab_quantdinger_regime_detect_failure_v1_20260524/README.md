# Strategy Lab QuantDinger Regime Detect Failure Investigation

Generated: 2026-05-24T13:12:28Z

## Session Declaration

Lane: Reporting
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Execution mode: AUDIT MODE
Intended files: task card plus this report bundle only
Contested surfaces touched: none
Collision risk: MEDIUM/HIGH by domain, LOW for repo writes
Decision: audit only

Target system layer: external QuantDinger sidecar evidence and Reporting artifacts.
Relevant contract rules: Tenn backend remains authoritative; external sidecar output is not canonical financial truth; no Tenn store, memory, parser, routing, or Strategy Lab status mutation is allowed.
What must not change: no Tenn DB, Qdrant, news, memory, canonical truth, Strategy Lab UI/status, token storage, paper orders, live trading, or transport integration.
Why safe: this investigation used saved report artifacts and source-level inspection only; no sidecar runtime was started.

## Verdict

`ROOT_CAUSE_CONFIRMED_SOURCE_LEVEL_NO_RUNTIME_RESMOKE`.

The HTTP 400 `single positional indexer is out-of-bounds` is an upstream QuantDinger endpoint bug triggered by certain valid candle counts, not a Tenn request/transport mutation issue.

The endpoint has two separate limitations:

- It requires camelCase `startDate` and `endDate`; snake_case already fails with a different message.
- Even with a valid camelCase request and at least 30 candles, segment construction can pass a 20-29 candle trailing segment into feature extraction, where feature extraction unconditionally reads `close.iloc[-30]`.

## Root Cause

In QuantDinger commit `91dd4e274702552b91036e2c89018622d111faee`, `ExperimentRunnerService.detect_regime()` parses only `startDate` / `endDate`, fetches candles, and calls `MarketRegimeService.detect()`.

`MarketRegimeService.detect()` rejects fewer than 30 total candles. That part is clear and would raise `At least 30 candles are required for regime detection`.

The actual May 24 failure is different. `_build_segments()` skips only segments shorter than 20 candles, but `_extract_features()` requires 30 candles because it reads `close.iloc[-30]`. Valid total candle counts such as 50-59, 80-89, and 119 leave a final 20-29 candle segment, which raises the observed Pandas `IndexError: single positional indexer is out-of-bounds`.

## Exact Reproduction / Request Payload

The exact manual probe request body is `DATA_MISSING`: `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/runtime_proof.json` persisted the HTTP 400 and message, but did not persist the body for `POST /api/agent/v1/experiments/regime/detect`.

The exact source-level reproduction is:

```text
MarketRegimeService.detect(<50-row OHLCV DataFrame>, symbol="BTC/USDT", market="Crypto", timeframe="1D")
```

Observed output:

```text
50: IndexError: single positional indexer is out-of-bounds
55: IndexError: single positional indexer is out-of-bounds
59: IndexError: single positional indexer is out-of-bounds
80: IndexError: single positional indexer is out-of-bounds
89: IndexError: single positional indexer is out-of-bounds
119: IndexError: single positional indexer is out-of-bounds
```

The most likely May 24 runtime payload is inferred, not artifact-confirmed:

```json
{
  "market": "Crypto",
  "symbol": "BTC/USDT",
  "timeframe": "1D",
  "startDate": "2026-04-05",
  "endDate": "2026-05-24"
}
```

Reasoning: the earlier successful Phase 1 request used `2026-04-05` to `2026-05-20` and returned 200; extending the same daily window to the manual probe date `2026-05-24` yields 50 daily candles if the provider returns one candle per calendar day, which is the first source-confirmed failing length. This remains an inference because the manual smoke script did not persist the regime request.

## Classification

- Bad request shape: no, not for the observed 400 message. Bad shape with snake_case dates produces `time data 'None' does not match format '%Y-%m-%d'`, not this error.
- Insufficient market rows: no, not the primary cause. Fewer than 30 rows raises the explicit 30-candle `ValueError`.
- Endpoint bug: yes. The segment minimum and feature minimum disagree.
- Fixture/data-window issue: yes as the trigger. Some otherwise valid date windows produce a trailing 20-29 candle segment.
- Expected limitation: partly. The 30-candle minimum is expected; the out-of-bounds message for valid 30+ candle windows is not expected.

## Narrow Fix Safety

A narrow upstream QuantDinger fix is safe in principle:

- Change `_build_segments()` to skip segments with fewer than 30 rows, or make `_extract_features()` explicitly reject/handle fewer than 30 rows before indexing `iloc[-30]`.
- Add regression coverage for 50-row, 55-row, and 80-row frames.
- Keep request validation explicit for missing `startDate` / `endDate` so client errors do not become Pandas internals.

This job did not edit QuantDinger or Tenn code because allowed writes were task/report artifacts only. A Tenn-side product-code fix is not safe or needed under this task card.

## Validation

No QuantDinger runtime was started. No live trading, paper orders, token storage, Tenn DB, Qdrant, news, memory, canonical truth, Strategy Lab status, UI, or transport integration was touched.

Validation performed:

- task card validation passed
- registry overlap check passed
- registry claim succeeded
- manual probe artifacts were read
- Phase 1 successful regime artifacts were read
- QuantDinger source commit `91dd4e274702552b91036e2c89018622d111faee` was inspected in `/tmp`
- source-level synthetic OHLCV reproduction confirmed exact failing candle-count classes

Final validation details are in `validation.json` and `diff-check.json`.

## Clean Re-Probe

A clean re-probe is justified only after the probe script is changed to persist the exact regime request body, response body, and fetched candle count.

Two safe options:

- Re-probe the known-good Phase 1 window `2026-04-05` to `2026-05-20` to confirm the sandbox still works.
- Re-probe a deliberately non-buggy 60-candle window after recording the request and candle count.

Do not set `current_sidecar_available=true` from the May 24 manual probe. The correct status is: read-only startup/backtest/denial cleanup passed, but regime detection is data-window fragile until the upstream endpoint is fixed or the probe pins a known-good window with captured row count.

## Save Recommendation

Save this as the root-cause record for the May 24 QuantDinger regime-detect failure:

`POST /api/agent/v1/experiments/regime/detect` failed because QuantDinger's regime segmentation can feed a 20-29 candle trailing segment into a feature extractor that requires 30 candles. Treat current regime support as `PENDING_REVIEW` / fragile, not clean sidecar availability.
