# Candlestick No-OHLC Current-Base Fix

Status: LOCAL_FIX_VALIDATED_READY_TO_PUBLISH

Issue: #275

Worktree:
`/home/l4nd0/tenn-issue275-candlestick-no-ohlc-current-base-v2-20260626`

Branch: `safe/issue275-candlestick-no-ohlc-current-base-v2-20260626`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@13400a462ec18fa7117eb48b3d54b0ff8f4647fa`

## Summary

The current-base fix makes `show_candlestick` return a structured
`DATA_MISSING` no-data chart response when backend OHLC history is empty,
instead of returning a raw HTTP 404 action failure.

No candles are fabricated, no external market data is fetched, no frontend
relabeling is added, and the existing successful chart path remains covered by
focused backend tests.

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `PR_BODY.md`
- `REVIEW.md`
