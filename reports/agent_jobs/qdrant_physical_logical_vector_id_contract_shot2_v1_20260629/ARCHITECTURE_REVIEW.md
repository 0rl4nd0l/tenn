# Architecture Review

`.cursor/rules/00_mandatory_index.md`, `backend_architecture.md`,
`embedding_rules.md`, `vector_store_invariants.md`, and `failure_policy.md`
were absent in this worktree. I used the active repo architecture source map
and docs: `SYSTEM_CONTRACT.md`, `03_data_model.md`,
`04_ingestion_pipeline.md`, `06_embeddings_and_vector_store.md`,
`08_backfill_contract.md`, `10_failure_model.md`,
`11_rebuild_and_recovery.md`, and `22_memory_ownership_map.md`.

## ARCHITECTURE REVIEW

### Change: logical vector IDs versus physical Qdrant point IDs

| Rule file | Section | Status | Explanation |
| --- | --- | --- | --- |
| SYSTEM_CONTRACT.md | 4.2 Deterministic Logical Vector IDs | COMPLIANT | The logical ID remains `document_id:chunk_index`; UUIDv5 is documented only as deterministic physical storage mapping. |
| 06_embeddings_and_vector_store.md | Vector store invariants | COMPLIANT | Qdrant remains the vector store, cosine/dimension rules unchanged, and no random vector/chunk IDs are introduced. |
| 03_data_model.md | Qdrant payload contract | COMPLIANT | `logical_vector_id` is a first-class payload field; physical point IDs are not canonical identity. |
| 04_ingestion_pipeline.md | Deterministic logical and physical point IDs | COMPLIANT | Pipeline writes logical IDs and delegates physical mapping to the adapter. |
| 10_failure_model.md | Fail-fast vector policy | COMPLIANT | No fallback, auto-repair, dimension, or distance behavior changed. |
| 22_memory_ownership_map.md | Architecture invariant interpretation | COMPLIANT | Random operational IDs remain separate from logical vector IDs. |

### Change: backend adapter and inspector enforcement

| Rule file | Section | Status | Explanation |
| --- | --- | --- | --- |
| SYSTEM_CONTRACT.md | Backend owns vector data | COMPLIANT | `upsert_points()` remains the backend adapter gate for normal writes. |
| 06_embeddings_and_vector_store.md | Payload validation remains strict | COMPLIANT | `asx_docs` now rejects point IDs that do not match `document_id:chunk_index`. |
| 11_rebuild_and_recovery.md | Qdrant inspector | COMPLIANT | Inspector now checks logical ID and deterministic physical point-ID mapping separately. |

### Summary

- COMPLIANT: 9
- VIOLATES RULE: 0
- REQUIRES MIGRATION: 0

### Verdict

APPROVED. This is the approved migration for issue #266 and keeps deterministic
identity, provenance, and rebuild/delete semantics intact.
