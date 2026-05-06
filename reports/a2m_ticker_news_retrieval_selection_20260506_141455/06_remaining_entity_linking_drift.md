# Remaining Entity Linking Drift

Entity linking was not changed.

The A2M trace showed partial drift: three core recall articles are A2M-linked, while some A2 Milk recall-mention articles are not fully linked. This task did not repair payloads, rewrite article rows, reindex Qdrant, or upsert/delete points.

Impact:

- Not a blocker for the v1 selection fix because audited ticker-filtered retrieval can already return the three core A2M-linked recall articles.
- Still a blocker for complete corpus coverage and recall consistency across all A2 Milk mentions.

Next handling should stay in a dedicated Provenance/ingestion-quality lane with explicit mutation gates.
