# Architecture Review

The `.cursor/rules/` architecture files referenced by the architecture-check
skill were not present in this worktree, so the closest repo architecture docs
were used:

- `docs/architecture/06_embeddings_and_vector_store.md`
- `docs/architecture/07_rag_contract.md`
- `docs/architecture/10_failure_model.md`
- `docs/architecture/17_agentic_chat_architecture.md`
- `docs/architecture/19_backend_api_surface.md`
- `docs/architecture/20_chat_learning_loop.md`
- `docs/architecture/21_cockpit_client_contract.md`

## Boundary Assessment

- Backend remains the owner of retrieval, financial truth, and readiness facts.
- Cockpit UI only fetches and renders readiness; it does not infer RAG/vector or
  financial truth from local client state.
- The readiness service is read-only: SQLite probes use existing files in
  read-only mode, Qdrant/model checks are HTTP GET probes, and no repair,
  backfill, embedding, Qdrant write, DB write, memory write, or action preview
  execution is performed.
- `memory_context` is explicitly marked `context_only` and is not counted toward
  normal financial-analysis readiness.
- `financial_truth_numeric` can remain visible in source metadata, but the
  delivered answer is suppressed when `DATA_MISSING` plus zero
  `claim_verified` sources would otherwise expose numeric claims as answer text.
