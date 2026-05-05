# Sample Review

## Samples Produced

- Expiry candidates sampled: 50
- Manual-review rows sampled: 30
- Blocked/uncertain rows sampled: 30
- Preserve rows sampled: 20

## Findings

Expiry sample: {'no_obvious_preserve_conflict_by_csv_mapping': 50}. The 50-row expiry sample had no entity-text-in-statement heuristic flags and no CSV mapping conflicts, so no obvious preserve-worthy row was found in that sample.

Blocked/uncertain sample: {'possible_future_manual_expiry_review': 30}. The 30-row blocked sample is mostly fanout-shaped but intentionally blocked by the prior audit because the statements are low-information or ambiguous. These rows may be proposed corrections for a later manual lane, but they are excluded from this first expiry action.

Manual and preserve samples remain unchanged; this dry run proposes no classification edits.
