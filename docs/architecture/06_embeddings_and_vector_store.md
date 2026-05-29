# Embeddings and vector store

Current embedding/runtime contract for backend retrieval surfaces.

## Live embedding runtime

The active embedding path is HTTP-based and resolves through the backend runtime
configuration, not a local CPU-only sentence-transformers stack.

Current implementation:

- `financial-engine_v2/backend/app/services/embeddings.py`
- `financial-engine_v2/backend/app/services/llamacpp_embeddings.py`
- `financial-engine_v2/backend/app/services/llamacpp_runtime.py`
- `financial-engine_v2/backend/app/services/llm.py`
- `financial-engine_v2/backend/app/config/model_routing.yaml`

Current checked-in routing config:

- `embedding_model: nomic-embed-text`
- `embedding_provider: local`
- `embedding_base_url: http://127.0.0.1:11434`

At runtime, embedding config is resolved through `resolve_embedding_runtime_config()`
and then executed through an OpenAI-compatible `/v1/embeddings` API path.

## Vector store invariants

- vector store: Qdrant only
- collection distance: cosine
- vector dimension must match the active collection schema
- payload validation remains strict for `asx_docs`
- vector IDs remain deterministic under the broader system contract

The SQLite prohibition for this layer means: do not use SQLite as a vector
store, canonical financial-truth store, embedding cache of record, or hidden
runtime retrieval fallback. It does not ban explicitly documented SQLite-backed
qualitative memory, operational state, feedback, or news-projection stores; see
`22_memory_ownership_map.md`.

Vector/chunk IDs must be deterministic `document_id:chunk_index` strings.
Operational/task/session IDs are outside the vector ID contract, provided they
do not become vector IDs, canonical financial IDs, or reproducibility keys.

## Runtime guards

The backend uses these guard surfaces:

- runtime embedding model artifact:
  - `reports/runtime_embedding_model.txt`
- vector baseline artifact:
  - `reports/vector_baseline.json`
- Qdrant collection validation:
  - collection vector size
  - collection distance
  - payload shape

Operational helper:

- `financial-engine_v2/scripts/verify_vector_baseline.py`

## Failure policy

Embedding/runtime failures are fail-fast:

- missing embedding endpoint
- embedding probe failure
- vector dimension mismatch
- unreachable Qdrant

The backend does not silently continue with a mismatched collection or undefined
embedding model.

## Historical note

Older docs may still describe embeddings as CPU sentence-transformers only.
That is no longer the primary runtime path in this repo.
