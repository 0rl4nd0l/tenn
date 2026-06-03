# Appendix 4D/4E Wrapper Metric Minimum Gate

Job: `extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602`
Lane: Financial Truth
Mode: SAFE EXTENSION

## Outcome

- Confident Appendix 4D/4E wrapper documents may now pass with two canonical
  metrics only when wrapper identity, wrapper disclosure evidence, and
  source-bound period/scale/currency context are present.
- NTA, dividends/distributions, record date, and associates/joint ventures
  remain disclosure-only.
- Ordinary annual and half-year reports still require the normal metric
  minimum.

## Verification

- Focused pytest: `17 passed`
- `py_compile`: pass
- `git diff --check`: pass
- Task-card `validate`: pass
- Task-card `check-diff`: blocked by pre-existing unrelated untracked files
- Targeted Appendix 4D verification: direct gate simulation on the known
  target payload returned `ok`

## No Broad Run

- No random sample
- No broad extraction
- No backfill
- No source PDF edits
- No DB/Qdrant/news/memory mutation
