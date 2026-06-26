# Decisions

## D1: Stop Exact Canonical-HEAD Equality

Decision: `last_verified_commit` is an audited source commit, not a field that
must equal current canonical HEAD after every docs merge.

Reason: exact equality creates a self-invalidating loop. A metadata PR changes
canonical HEAD when it merges, making its own freshly written metadata stale.

## D2: Add Separate Freshness Check Fields

Decision: add `freshness_checked_at` and `freshness_checked_against` for
metadata-only freshness checks.

Reason: this preserves the useful audited snapshot while still recording the
current canonical commit used for the latest freshness check.

## D3: Use Ancestor Plus Behavior-Stale Files

Decision: freshness is valid when the audited commit is an ancestor of current
canonical and no behavior-affecting `stale_if_files` changed without newer
validation.

Reason: this catches real skill-surface drift without forcing churn for harmless
metadata-only refreshes.

## D4: Do Not Touch Extraction

Decision: no extraction, runtime, product, data, prompt, parser, or financial
truth files are in scope.

Reason: this lane fixes a control-plane documentation loop only.
