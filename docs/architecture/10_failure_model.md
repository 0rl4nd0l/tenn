# Failure model

This document describes how the system behaves when dependencies or operations fail. Behavior is categorized as **fail-fast**, **retry**, or **skip** as defined below.

## Behavior categories

- **Fail-fast**: Abort immediately; do not proceed or fall back. Used for misconfiguration, invariant violations, and startup validation. The caller receives an error; no silent degradation.
- **Retry**: Treat as transient; the operation may be retried by the caller or infrastructure (e.g. Celery task retry, HTTP client retry). Used for temporary unavailability of a service.
- **Skip**: Continue with the rest of the batch or workflow; record the failure for the single item; do not abort the whole operation. Used for per-item failures in batch jobs.

---

## Failure matrix

| Failure Type | Component | Expected Behavior | Remediation |
|--------------|-----------|-------------------|-------------|
| **Ollama unavailable** | Backend startup, RAG, pipeline, cockpit | **Startup**: fail-fast — startup validates embedding model by calling Ollama; if unreachable or no vector returned, raise and do not start. **RAG query**: if embedding call fails or returns empty, request fails (no silent fallback). **Pipeline/worker**: task fails; Celery can retry (retry). **Cockpit**: health check warns; chat/embed calls fail (retry by user). | Ensure Ollama is running and `nomic-embed-text` (or configured model) is pulled. For transient outages, rely on task/request retry. |
| **Qdrant unavailable** | Backend startup, RAG, pipeline | **Startup**: fail-fast — startup connects to Qdrant and validates collection; connection failure prevents startup. **RAG query**: request fails with 503. **Pipeline upsert**: task fails (retry). | Ensure Qdrant is running and reachable. Retry transient connection failures. |
| **Dimension mismatch** | RAG, pipeline, embeddings | **Fail-fast**. On startup and at upsert/query, collection vector size must match embedding dimension. `ensure_collection` / `validate_qdrant_collection` raise `RuntimeError` if existing collection dimension ≠ expected. | Recreate the Qdrant collection with the correct dimension (e.g. via rebuild RAG index) or change embedding model and rebuild; do not run with mismatch. |
| **Distance mismatch** | RAG, pipeline, embeddings | **Fail-fast**. Collection must use COSINE distance. Validation raises if collection uses a different distance (e.g. DOT, EUCLID). | Recreate the collection with COSINE distance; do not run with mismatch. |
| **Embedding model mismatch** | Backend startup | **Fail-fast**. Startup compares `settings.embed_model` to the value stored in `reports/runtime_embedding_model.txt`; mismatch raises (RAG index was built with another model). | Align config with the model used to build the index, or run rebuild and update stored model file. |
| **PDF missing / not readable** | Pipeline (process_document), download | **Per-document**: fail for that document. **Batch (backfill)**: skip — record error in batch result, continue with next document. Single-document task fails (retry may not help until PDF is fixed). | Ensure PDF exists at `pdf_path` and is valid; re-download if missing; for corrupted PDFs, fix source or skip that document. |
| **Provider returns empty payload (OpenBB)** | OpenBB sidecar provider (price, fundamentals) | **Fail-fast** for that request. `OpenBBSidecarProvider` raises `OpenBBSidecarProviderError` if response is empty or not a dict. No silent fallback. | Check sidecar health and upstream; caller may retry (retry). |
| **DB connection failure** | Backend, worker, API | **Startup**: fail-fast if DB is required for startup (e.g. `create_all`). **Request/task**: operation fails; connection errors propagate. Celery tasks can retry (retry). | Ensure Postgres is reachable; fix connection settings; use retries for transient outages. |

---

## Summary by category

- **Fail-fast**: Dimension mismatch, distance mismatch, embedding model mismatch; Qdrant/Ollama/DB unreachable at **startup**; OpenBB empty payload; RAG disabled or misconfigured (per backend rules).
- **Retry**: Ollama/Qdrant/DB transiently unavailable at **request or task** time; OpenBB empty due to transient issue; task-level failures where retry is meaningful.
- **Skip**: Per-document failures in batch backfill (e.g. one PDF corrupt or missing, one document extraction failure); duplicate source_url handling (skip insert).

---

## References

- [.cursor/rules/backend_architecture.md](../../.cursor/rules/backend_architecture.md) — no silent degradation; fail fast on config errors.
- [07_rag_contract.md](07_rag_contract.md) — RAG API contract.
- [11_rebuild_and_recovery.md](11_rebuild_and_recovery.md) — rebuild and recovery after index/config mismatch.
