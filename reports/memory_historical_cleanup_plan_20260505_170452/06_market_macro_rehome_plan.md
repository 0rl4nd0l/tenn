# Market And Macro Rehome Plan

Market/macro rows in company memory should not be deleted simply because they are in the wrong store. They may be useful context, but the current source/provenance gaps make automatic rehome unsafe.

Future rehome requirements:

1. Operator reviews `memory_rows_rehome_market_macro_candidates.csv`.
2. Candidate row source provenance is checked against source registry and memo JSONL.
3. Destination is selected as `market_memory.sqlite:sector_states` or `market_memory.sqlite:macro_state`.
4. Rehome design decides whether to copy-then-expire, expire-then-manual-add, or leave row in place with source-label correction. No source-label or synthesis change is allowed in this plan.
5. Any rehome must preserve original row id, original company scope, source, source_id, and full statement text in an audit manifest.
