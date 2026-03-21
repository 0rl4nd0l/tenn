# Intelligence Pack Review

Analyzes the latest weekly intelligence pack JSON and produces an executive-readable brief. **Read-only** — do not modify the database, Qdrant, or the weekly JSON file.

## Instructions

1. **Locate latest file**: Glob `reports/weekly/*.json`. Pick the file with the most recent name/timestamp (e.g. `YYYYMMDD_HHMMSS.json`).
2. **Load and read** the JSON. Expected top-level keys: `document_count`, `ticker_count`, `total_risk_flags`, `total_high_risk_documents`, `by_ticker`, `new_tickers_over_3_mentions`, `rag_summary`, `generated_at_utc`, `window_days`, `window_since_utc`.

## Analysis Steps

1. **Aggregate check**: Confirm and cite `document_count`, `ticker_count`, `total_risk_flags`, `total_high_risk_documents`.
2. **By-ticker**: Use `by_ticker` for per-ticker counts and risk intensity.
3. **New / spike**: Use `new_tickers_over_3_mentions`; infer "sudden spike" only if data supports it.
4. **RAG**: Inspect `rag_summary.rag_response` for themes and recurring catalysts; do not call RAG again.

## Output Structure

Produce exactly four sections in this order:

---

### SECTION 1: Risk Concentration
- **Top 3 tickers by risk flags** with counts.
- **Risk intensity ratio**: `risk_flags_count / document_count` per ticker; note `high_risk_document_count`.

### SECTION 2: Emerging Risk Signals
- **New tickers crossing threshold**: list `new_tickers_over_3_mentions`.
- **Sudden spike patterns**: only if data supports it; otherwise state "No clear spike pattern in this pack."

### SECTION 3: Retrieval Insight
- **Risk themes** from `rag_summary`: clustered by sector, geography, or catalyst type.
- **Catalysts** that repeat across the RAG summary.
- If `rag_summary.ok` is false or missing: "RAG summary unavailable; skip retrieval insight."

### SECTION 4: Recommended Follow-Up Queries
- Exactly **3** targeted RAG queries (short, concrete questions) based on this pack. Do not execute them.

---

## Constraints

- Do not connect to or modify the database.
- Do not modify or write to Qdrant.
- Do not overwrite or rewrite the weekly JSON file.
- Only read the latest JSON and produce the four-section analysis.
