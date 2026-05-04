# Data model

This document describes canonical identifiers, key database entities, provenance fields, and the Qdrant payload contract. For concrete field definitions and tables, see models in `backend/app/models/`.

## Canonical identifiers

- **document_id**: UUID. Canonical form when serialized (e.g. in APIs or vector payloads) is **lowercase string** (e.g. `a1b2c3d4-e5f6-7890-abcd-ef1234567890`). Stored as UUID in the database; string representation must be consistent for deduplication and vector ID construction.

- **Vector IDs**: Composite string `document_id:chunk_index`, where `document_id` is the canonical lowercase UUID string and `chunk_index` is the zero-based index of the chunk within that document. Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890:0`. Vector IDs are not bare UUIDs.

## Key DB entities (high level)

- **Document** (`documents`): Core entity for ingested documents. Holds ticker, exchange, doc_class, doc_subtype, title, source_url, pdf_path, published_at, ingested_at, etc. See `backend/app/models/documents.py`.

- **Extracted metrics**: Financial figures extracted from documents.
  - **ExtractionRun** (`extraction_runs`): Per-document extraction run (document_id, status, structured_json, confidence, etc.). See `backend/app/models/extractions.py`.
  - **ASXPeriodicFinancial** (`asx_periodic_financials`): Periodic financial metrics (ticker, period_end, period_type, revenue, ebit, np_attributable, cash flows, etc.) linked via `source_document_id`. See `backend/app/models/asx_financials.py`.

- **Risk notes**: **ASXRiskNote** (`asx_risk_notes`): One row per document (document_id PK); risk_summary, risk_bullets, guidance_summary, material_changes. See `backend/app/models/asx_financials.py`.

Other entities (e.g. OpenBB snapshots) exist in the repo; see `backend/app/models/` for the full set.

## Provenance fields to track

- **published_at**: When the document was originally published (nullable on Document).
- **ingested_at**: When the document was ingested into the system (server default on Document).
- **Source / provider**: Document origin. On Document this is represented by **source_url**. Discovery and ingestion may also record which **provider** (e.g. provider_network) supplied the document; provider is not stored on Document itself but may appear in staging or discovery payloads.

## Qdrant payload contract

Every point in the RAG collection must have a payload that includes the following fields (used for filtering, display, and validation):

| Field         | Description                                      |
|---------------|--------------------------------------------------|
| document_id   | Canonical lowercase UUID string                  |
| ticker        | Ticker symbol                                    |
| doc_class     | Document class (e.g. announcement)               |
| doc_subtype   | Document subtype (e.g. periodic)                 |
| chunk_index   | Zero-based chunk index within the document       |
| title         | Document title                                   |

Payloads are written in the pipeline when upserting vectors and validated on read in RAG search. Missing or invalid `document_id` in a payload causes runtime errors. See `backend/app/services/pipeline.py` (payload construction) and `backend/app/services/rag.py` (validation).
