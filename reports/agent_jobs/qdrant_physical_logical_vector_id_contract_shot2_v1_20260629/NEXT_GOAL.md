# Next Goal

Recommended next prompt:

```text
/goal Review local issue #266 Shot 2 at /home/l4nd0/tenn-issue266-qdrant-vector-id-contract-shot2-v1-20260629, then if safe publish a draft PR for branch safe/issue266-qdrant-vector-id-contract-shot2-v1-20260629. Do not merge, mark ready, or run live Qdrant/backfill/reindex without explicit approval.
```

If live runtime proof is wanted later, create a separate runtime/data-approved
task card first. This implementation deliberately did not mutate Qdrant.
