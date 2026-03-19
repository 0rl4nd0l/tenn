# PDF extraction and chunking

Standards for PDF path resolution, text extraction quality, chunking behavior, and QA tooling. This document defines expected behavior and quality criteria; it does not prescribe implementation changes.

---

## 1. PDF path resolution

PDF paths are **resolved relative to a configurable docs root** so that the same logical layout is shared by the API, workers, and any scripts that read or write PDFs.

- **Where resolution happens**: `_resolve_pdf_path()` in `financial-engine_v2/backend/app/services/pipeline.py`. It is used when reading a document for extraction and embedding (e.g. before `extract_text_from_pdf`).
- **Configuration**: `docs_root` is defined in `app.core.config` (default: `{DATA_ROOT}/asx/docs`). It is resolved at startup via `_resolve_project_path()` so that relative project paths work across environments.
- **Rules**:
  - Empty or blank `pdf_path` is returned unchanged.
  - **Absolute** paths (after `expanduser`) are returned as-is.
  - **Relative** paths are resolved as `(docs_root / path).resolve()`, so all relative paths are under `docs_root`.
- **Directory layout**: Document PDFs are stored under `docs_root` by ticker, e.g. `docs_root/{TICKER}/{date}_{slug}_{document_id}.pdf`. Building and resolving paths for new documents uses `_doc_path()` / `_canonical_doc_pdf_path()` with the same `docs_root`.

---

## 2. Expected properties of extracted text

Extraction produces a single plain-text string per PDF. The following are **quality standards** for that text; pipelines and QA should treat them as requirements.

| Property | Standard |
|----------|----------|
| **Minimum length** | Extracted text should meet a minimum character count per page (e.g. not empty or near-empty pages). Pages that yield only a few characters after extraction are candidates for re-extraction or manual review. |
| **Non-garbled** | Text should be readable: no systematic character substitution, broken encoding, or repeated symbols that indicate extraction or PDF corruption issues. |
| **Page completeness** | Where page boundaries are known, each page’s content should be present and ordered. Truncation or missing pages should be detectable (e.g. via page count vs. content length heuristics or explicit page markers). |

Current extraction is implemented in `app.services.text_extract` using PyMuPDF (`fitz`), concatenating `page.get_text("text")` for all pages. Any future extractor (e.g. `pdftotext` or other backends) must satisfy the same properties above.

---

## 3. Chunking goals

Chunking turns extracted text into segments for embedding and retrieval. The following are **target standards**; implementations should aim for them even if current code does not yet fulfill all of them.

- **Target size range**: Chunks should fall within a defined character (or token) range (e.g. a minimum and maximum size) so that retrieval returns coherent, neither too small nor too large, units of context.
- **Sentence boundaries**: Splits should prefer sentence boundaries where possible to avoid cutting mid-sentence, which degrades readability and embedding quality.
- **Header/footer repetition**: Repeated headers and footers (e.g. company name, “Confidential”, page numbers) should not dominate chunks. Chunking or pre-processing should reduce or normalize such repetition so that it does not skew embeddings or retrieval.

Current implementation: `app.services.chunking.simple_chunk(text, max_chars=4500)` does fixed-size splitting with no overlap and no sentence-boundary or header/footer handling. Pipeline call site: `pipeline.process_document()` uses `simple_chunk(text, max_chars=4500)`. Future work may introduce overlap, sentence-aware splitting, and header/footer filtering while staying within the goals above.

---

## 4. PDF Quality QA

Scripts and tools used to validate extraction and chunking quality, and to inspect the vector store that holds chunk embeddings.

| Tool | Status | Purpose |
|------|--------|---------|
| **inspect_qdrant_collection.py** | Existing | Read-only inspection of the RAG Qdrant collection. Reports collection metadata, point count by ticker, duplicate point IDs, missing `chunk_index` sequences per document, and payload/id integrity. Does not modify the collection. Location: `financial-engine_v2/scripts/inspect_qdrant_collection.py`. |
| **PDF quality audit harness** | Planned | Placeholder for a dedicated harness that audits PDF extraction and chunking quality (e.g. per-document or per-page checks for minimum length, garbled text, completeness, and chunk size/distribution). Not yet implemented. |

---

## References

- Path resolution: `financial-engine_v2/backend/app/services/pipeline.py` — `_resolve_pdf_path`, `_doc_path`, `_canonical_doc_pdf_path`.
- Config: `financial-engine_v2/backend/app/core/config.py` — `docs_root`.
- Extraction: `financial-engine_v2/backend/app/services/text_extract.py` — `extract_text_from_pdf`.
- Chunking: `financial-engine_v2/backend/app/services/chunking.py` — `simple_chunk`.
- Pipeline usage: `financial-engine_v2/backend/app/services/pipeline.py` — `process_document()`.
