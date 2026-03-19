# Embeddings and vector store

This document defines the **hard invariants** for the RAG embedding and vector store stack. These are not configurable alternatives; they are fixed choices. Violations must fail fast—no silent fallbacks.

## Hard invariants

### Embeddings

- **Embeddings: local CPU Sentence Transformers only.** All text embedding for RAG is produced via a local `sentence-transformers` runtime on CPU.
- **Model: configured `EMBED_MODEL` only.** Index and query embeddings must come from the same configured Sentence Transformers model.

### Vector store

- **Vector DB: Qdrant only.** All vector storage and similarity search for RAG is done in Qdrant. No other vector store (e.g. Pinecone, Weaviate, pgvector) is used.
- **Distance: COSINE only.** Collection vectors use `Distance.COSINE`. No other distance (e.g. Euclidean, dot product) is allowed.

### Dimension and schema

- **Dimension must match collection schema.** The embedding dimension produced by the model must equal the collection’s vector size. Any mismatch causes a **hard failure** at startup or at collection validation; the application does not start or proceed with a wrong dimension.

### Guards

- **Model guard: `runtime_embedding_model.txt`.** The backend writes the current routed embedding model to `reports/runtime_embedding_model.txt` (under the project root). On startup, if this file exists, its value is compared to the active embedding role from `backend/app/config/model_routing.yaml`. If they differ, the application raises and exits. This blocks accidental model switches without an explicit RAG rebuild.
- **Cutover warning:** Validate the Sentence Transformers vector dimension against the existing Qdrant collection before startup. The backend probes the active embedding model during boot and fails fast on dimension mismatch.
- **Vector baseline guard: `vector_baseline.json` and verify script.** After a full RAG index rebuild, `rebuild_rag_qdrant_index` writes `reports/vector_baseline.json` with `vector_count` and metadata. The script `financial-engine_v2/scripts/verify_vector_baseline.py` compares the current Qdrant collection count to this baseline; if the difference exceeds the allowed tolerance (e.g. 5%), the script exits with code 1. Use this in CI or ops to detect unexpected index drift or partial wipes.

## Why no fallbacks

We do **not** provide fallbacks (e.g. alternate embedding APIs, alternate vector DBs, or alternate distance metrics) for these reasons:

1. **Reproducibility.** One embedding provider, one model, one vector store, one distance metric give deterministic, comparable behavior across environments and over time. Fallbacks would make behavior environment-dependent and harder to reason about.
2. **Index consistency.** Vectors are only meaningful with the same model and distance. Mixing providers or models would corrupt retrieval quality; “fallback” would imply running with an incompatible index, which we treat as invalid.
3. **Explicit failure over silent drift.** If the embedding runtime or Qdrant is down, or the model or dimension is wrong, we fail fast so operators fix the real dependency instead of silently degrading into an undefined state.
4. **Operational clarity.** A single path simplifies configuration, debugging, and runbooks. No branching on “which embedding backend is in use” or “which vector store we wrote to.”

To change any of these choices (e.g. new model or new distance), you must explicitly change the code/config, rebuild the RAG index, update the baseline and model guard file, and treat it as a controlled migration—not a runtime fallback.
