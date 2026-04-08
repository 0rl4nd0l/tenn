# RAG contract

This document defines the HTTP contract for the RAG (retrieval-augmented generation) query endpoint: request/response shape, hit structure, error behavior, and fail-fast rules.

## Endpoint

**`POST /rag/query`**

Request and response are JSON. No path or query parameters; all inputs are in the request body.

---

## Request

| Field   | Type   | Required | Description |
|--------|--------|----------|-------------|
| `query` | string | yes | Natural-language search query. Must be non-empty after trim. |
| `source` | `"asx_docs" \| "news" \| "commentary" \| "hybrid"` | no | Retrieval source selector. Defaults to `"asx_docs"`. |
| `ticker` | string \| null | no | Optional ticker symbol (e.g. `"BHP"`). When set, results are filtered to that ticker. |
| `top_k` | integer | no | Maximum number of hits to return. Default `8`; clamped to at least 1. |
| `debug` | boolean | no | If supported, set to `true` to include a `debug` object in the response (score distribution, embedding norm, etc.). |
| `provider` | string \| null | no | Optional news-provider filter (used with `source="news"`). |
| `language` | string \| null | no | Optional news-language filter (used with `source="news"`). |
| `date_from` | string \| null | no | Optional news lower date bound (used with `source="news"`). |
| `date_to` | string \| null | no | Optional news upper date bound (used with `source="news"`). |

### Source behavior

- `source="asx_docs"`: implemented.
- `source="news"`: implemented.
- `source="commentary"`: currently returns HTTP `501` (not implemented via `/rag/query`; use `/chat`).
- `source="hybrid"`: currently returns HTTP `501` (not implemented via `/rag/query`; use `/chat`).

---

## Response shape

- **`ok`** (boolean): `true` when the request was processed successfully (even if there are zero hits).
- **`hits`** (array): List of hit objects (see below), ordered by relevance (score descending).
- **`candidate_count`** (integer): Number of candidates returned by the vector search before any post-filtering.
- **`filtered_count`** (integer): Number of hits after validation (typically equals `candidate_count` unless invalid payloads are dropped).
- **`debug`** (object, optional): Present only when `debug: true` was requested and supported. Contains diagnostic fields such as `embedding_norm`, `score_distribution`, `hit_ticker_distribution`, `top_payload_keys`, `collection_dimension`.

---

## Hit structure

Each element of `hits` is an object with:

| Field         | Type            | Description |
|---------------|-----------------|-------------|
| `score`       | number          | Similarity score (e.g. cosine similarity; higher is more similar). |
| `ticker`      | string          | Ticker symbol for the document (may be empty string). |
| `title`       | string          | Document title (may be empty string). |
| `document_id` | string          | UUID of the source document. |
| `doc_class`   | string \| null  | Document class from payload (e.g. announcement type). |
| `doc_subtype` | string \| null  | Document subtype from payload. |
| `chunk_index` | number \| null  | Index of the chunk within the document. |

---

## Behavior when RAG is disabled

If embeddings or Qdrant is disabled in configuration (`enable_embeddings` or `enable_qdrant` false), the service does not perform vector search. The endpoint returns:

- **HTTP 503** with a JSON body describing that the RAG backend is disabled (e.g. `"RAG backend is disabled (embeddings disabled)"` or `"RAG backend is disabled (qdrant disabled)"`).

Callers should treat 503 as “RAG temporarily unavailable” and avoid retrying with the same request in a tight loop.

---

## Fail-fast and error rules

- **Empty or missing `query`**: returns **400** with a message that `query` is required.
- **RAG disabled** (embeddings or Qdrant off): returns **503** (see above).
- **Dimension mismatch**: The runtime embedding model’s vector size must match the Qdrant collection’s vector size. If the collection exists but has a different dimension, the service raises at startup (application fails to start) or at query time (e.g. **503** from `ensure_collection` / validation).
- **Distance mismatch**: The collection must use the expected distance metric (e.g. COSINE). Mismatch is treated like dimension mismatch (startup or **503**).
- **Missing collection**: If the configured Qdrant collection does not exist, startup validation fails (application does not start). If a query path discovers a missing collection, the service returns **503**.
- **Embedding model mismatch**: If the runtime embedding model name differs from the model that was used to build the index (as recorded in the stored expectation file), the application fails at startup with a clear error; no automatic rebuild is performed.
- **Invalid payload in Qdrant** (e.g. missing or invalid `document_id`): the service may raise and return **502** or **503** depending on how the error is mapped.

All of the above are fail-fast: the system does not silently return wrong or partial results when configuration or index state is invalid.

---

## Example requests and responses

### Example 1: Minimal request (no ticker, default top_k)

**Request**

```http
POST /rag/query
Content-Type: application/json

{
  "query": "capital expenditure guidance"
}
```

**Response (200)**

```json
{
  "ok": true,
  "hits": [
    {
      "score": 0.891,
      "ticker": "BHP",
      "title": "Quarterly Report Q3 FY24",
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "doc_class": "announcement",
      "doc_subtype": "quarterly",
      "chunk_index": 2
    }
  ],
  "candidate_count": 1,
  "filtered_count": 1
}
```

### Example 2: Ticker filter and debug

**Request**

```http
POST /rag/query
Content-Type: application/json

{
  "query": "dividend policy",
  "ticker": "CBA",
  "top_k": 5,
  "debug": true
}
```

**Response (200)**

```json
{
  "ok": true,
  "hits": [
    {
      "score": 0.872,
      "ticker": "CBA",
      "title": "Annual Report 2024",
      "document_id": "f0e1d2c3-b4a5-9687-6543-210fedcba987",
      "doc_class": "announcement",
      "doc_subtype": "annual",
      "chunk_index": 0
    }
  ],
  "candidate_count": 1,
  "filtered_count": 1,
  "debug": {
    "embedding_norm": 1.0,
    "score_distribution": { "min": 0.872, "max": 0.872, "mean": 0.872, "std": 0.0 },
    "hit_ticker_distribution": { "CBA": 1 },
    "top_payload_keys": ["document_id", "ticker", "title", "doc_class", "doc_subtype", "chunk_index"],
    "collection_dimension": 1024
  }
}
```
