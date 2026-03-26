# Domain Skill: Financial Pipeline

## Source Trace
- `docs/architecture/04_ingestion_pipeline.md` (Confirmed — referenced)
- `docs/architecture/05_pdf_extraction_and_chunking.md` (Confirmed — referenced)
- `docs/architecture/06_embeddings_and_vector_store.md` (Confirmed — referenced)
- `docs/architecture/07_rag_contract.md` (Confirmed — referenced)
- `docs/architecture/08_backfill_contract.md` (Confirmed — referenced)
- `docs/architecture/09_worker_and_celery_contract.md` (Confirmed — referenced)
- `docs/architecture/12_evaluation_and_drift_monitoring.md` (Confirmed — referenced)
- `docs/ops/financial_metrics_extraction_analysis.md` (Confirmed — referenced)
- `docs/ops/pdf_parsing_assessment_report.md` (Confirmed — referenced)
- `docs/ops/news_baseline_policy.md` (Confirmed — referenced)
- `docs/ops/ticker_quarantine.md` (Confirmed — referenced)

---

## Domain Context

This pipeline processes **ASX (Australian Securities Exchange) announcements**:
- Financial reports (annual, half-year, quarterly)
- Market-sensitive announcements
- News and market data (via EODHD fallback and OpenBB sidecar)

**Critical constraint:** Do not fabricate financial values, extraction outputs, metrics, or data lineage. If extraction fails or data is absent, the correct behavior is to record the failure — not to estimate or interpolate.

---

## Pipeline Stages and Ownership

| Stage | What It Does | Key File/Doc |
|-------|-------------|--------------|
| Discovery | ASX metadata → Postgres document rows (deduped) | `04_ingestion_pipeline.md` |
| Download | PDFs → `DATA_ROOT/docs/` filesystem | `04_ingestion_pipeline.md` |
| Extraction | PDF text → structured text (PyMuPDF primary, Docling/Tesseract for complex) | `05_pdf_extraction_and_chunking.md` |
| Chunking | Text → chunks with metadata | `05_pdf_extraction_and_chunking.md` |
| Embedding | Chunks → vectors via embed role (Ollama `nomic-embed-text`) | `06_embeddings_and_vector_store.md` |
| Upsert | Vectors → Qdrant with deterministic IDs | `06_embeddings_and_vector_store.md` |
| Financial extraction (optional) | Chunks → structured financial rows via reasoning role | `04_ingestion_pipeline.md` |
| RAG query | Query → Qdrant retrieval → LLM synthesis → response | `07_rag_contract.md` |

---

## Critical Invariants

**Vector IDs are deterministic.**
Changing the ID generation logic will break deduplication. Upserts rely on stable IDs for idempotency. Before changing any ID generation code, read `06_embeddings_and_vector_store.md` and verify the full upsert flow.

**RAG collection name: `commentary_chunks`**
Not `asx_docs`. `commentary_chunks_v2` is an optional fallback. The active collection is controlled by `settings.qdrant_collection` (set via env or config). Switching to `v2` requires updating that setting — it is not automatic code-level fallback. Ticker-filter support applies only to `asx_docs` collection; `commentary_chunks` does not filter by ticker. Do not change the collection routing without reading `07_rag_contract.md`.

**Financial rows must come from actual extraction.**
Do not write synthetic or interpolated values to Postgres financial tables. Extraction failure is acceptable and must be recorded as-is.

**Gate scripts define correctness thresholds.**
`validate_financial_metrics_gates.py` and `validate_financial_coverage_gates.py` encode expected quality floors. Do not modify thresholds to make failing gates pass — investigate the root cause of the regression.

**Financial metrics gate conditions** (from `scripts/validate_financial_metrics_gates.py` — Confirmed):
- `duplicates == 0` — zero duplicate rows (same entity + metric + period + statement family + definition scope + value type + balance position + duration group)
- `conflicts == 0` — zero conflicting values for the same key
- `empty_currency == 0` — zero rows with missing currency where currency is required
- All three must be zero for `gate_pass: true`

---

## PDF Extraction

- **Default:** PyMuPDF `find_tables()` — fast (~1-25s), no ML models, preserves 2D table structure. Set via `EXTRACTION_BACKEND=pymupdf` (default).
- **Opt-in:** Docling (`EXTRACTION_BACKEND=docling`) — IBM layout model + TableFormer. Much slower (120s+), often times out on ASX filings. Only useful for complex/scanned PDFs.
- Both backends produce the same `StructuredDocument` (tables + sections) consumed by the multipass extraction pipeline.
- Cache: `{pdf}.pymupdf.json` / `{pdf}.docling.json` — second runs are instant.
- Known issues: see `docs/ops/pdf_parsing_assessment_report.md`

Before changing extraction logic, read `05_pdf_extraction_and_chunking.md` and `backend/app/services/docling_extract.py`.

---

## Financial Metrics Extraction

The financial extraction subsystem extracts structured rows (earnings, revenue, guidance, capital allocation, balance-sheet risk metrics) from PDF text using the reasoning/deep_reasoning model role.

Failure modes and known limitations: `docs/ops/financial_metrics_extraction_analysis.md`

Do not add new metric types without updating the extraction schema and gate scripts.

---

## Ticker Quarantine

Some tickers are quarantined due to data quality issues. Check `docs/ops/ticker_quarantine.md` before processing or reporting on specific tickers.

---

## News and Market Data

- Primary: ASX discovery
- Fallback: EODHD (news sparsity fallback; see `docs/ops/news_sparsity_investigation.md`)
- Optional: OpenBB sidecar (`financial-engine_v2/openbb_sidecar/`)
- Policy: `docs/ops/news_baseline_policy.md`

Do not introduce new news sources without updating the news baseline policy.

---

## Evaluation and Drift Monitoring

See `docs/architecture/12_evaluation_and_drift_monitoring.md`.

Canonical regression baseline: `reports/baselines/canonical_eval_baseline_latest.json`
Required eval fixtures:
- `reports/news_eval_queries.json`
- `reports/company_eval_queries.json`
- `reports/eval_queries.json`

Drift = output divergence from baseline beyond gate thresholds. Any drift must be investigated, not worked around.

---

## Backfill

For historical document backfill, read `docs/architecture/08_backfill_contract.md` before triggering or modifying backfill behavior. Backfill interacts with the same Postgres + Qdrant surfaces as the live pipeline.

---

## Celery/Worker Contract

For any change affecting async task dispatch, read `docs/architecture/09_worker_and_celery_contract.md`.
The Celery surface lives in `financial-engine_v2/backend/app/celery_app.py` and `worker_tasks.py`.
Do not add tasks that bypass the router or write directly to Qdrant outside the established upsert path.
