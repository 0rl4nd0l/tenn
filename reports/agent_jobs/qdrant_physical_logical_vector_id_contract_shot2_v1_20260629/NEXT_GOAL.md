# Next Goal

Recommended next prompt:

```text
/goal Review draft PR #473 for issue #266 at /home/l4nd0/tenn-issue266-qdrant-vector-id-contract-shot2-v1-20260629 after the branch refresh onto canonical cc750c83. Verify current GitHub checks and base freshness before any readiness claim. Do not merge, mark ready, close issue #266, or run live Qdrant/backfill/reindex without explicit approval.
```

If live runtime proof is wanted later, create a separate runtime/data-approved
task card first. This implementation deliberately did not mutate Qdrant.
