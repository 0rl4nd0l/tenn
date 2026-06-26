# Code Review

Reviewer: Codex
Scope: issue #260 publish lane, source/test diff only
Date: 2026-06-26

## Result

PASS: no blocking findings.

## Checks

- Verified `compute_recency_decay()` now uses `exp(-ln(2) * age / half_life)`,
  so one configured half-life interval returns `0.5`.
- Verified non-positive or missing half-life behavior is unchanged: returns
  `1.0`.
- Verified fixed-timestamp tests cover direct helper behavior and source
  weighting for `news_article` plus `market_commentary`.
- Verified marketplace change is a stale-comment update only.

## Residual Risk

This branch changes the scoring semantics intentionally. Existing downstream
ranking that depends on recency decay will shift after merge, but that is the
issue #260 acceptance target.
