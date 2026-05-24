# Memory Live Inventory Read-Only

Read-only inventory completed against the live source-registry memory root.

Findings:
- Active company-memory rows: 147 across 59 active company IDs.
- Active duplicate-statement contamination clusters: 0.
- Active source-fanout suspicious clusters: 4 covering 17 entries.
- Offline read-path simulation says 17 suspicious entries are selectable under current active-score semantics.
- Market-memory unsupported linked ticker tokens: 19.

No memory cleanup, deletion, rewrite, migration, alias canonicalisation, reindex, or chat/context write path was run. Before/after hashes matched for company, market, and thesis memory stores.

Next safe step: separate approval-gated quarantine/read-path suppression or cleanup task after manual review confirms which source-fanout clusters are contamination.
