# Evaluation Source Assets

This folder contains metadata-only source asset manifests for extraction
evaluation fixtures. It must not contain raw PDFs.

The manifest is a reviewability contract only. Resolver results can show that a
local source PDF is present, missing, or metadata-mismatched, but source
openability never counts as metric correctness.

- `confirmed_metric_coverage_source_assets.json` keeps the broader metadata-only
  source asset contract for real-gold and confirmed metric coverage fixtures.
- `real_gold_review_source_assets.json` is the issue #99 real-gold review
  manifest. It records fixture/source bindings plus size and SHA256 identity
  metadata for the 15 committed real-gold fixtures, while keeping the raw PDFs
  off-git.
