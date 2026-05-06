# Next Codex Prompt: Source Label Semantics

Lane: Provenance or Reporting
Execution mode: AUDIT MODE first, then SAFE EXTENSION MODE only after source contract review.

Task:

Audit and fix user-visible source-label semantics for local news evidence in Cockpit answers and source drawer output.

Inputs:

- `reports/a2m_news_trace_20260506_110151/07_reporting_freshness_and_source_label.md`
- `reports/a2m_news_trace_20260506_110151/09_root_cause_verdict.md`
- `reports/a2m_ticker_news_retrieval_selection_20260506_141455/03_retrieval_selection_contract.md`

Requirements:

- Do not change retrieval selection.
- Do not mutate Qdrant, SQLite, or memory.
- Do not change financial truth.
- Preserve source metadata emitted by ticker-filtered news retrieval.
- Add tests proving local news evidence is not labeled as generic internet/search evidence.
- Keep holdings/local personal data source labels separate from public/local news source labels.

Validation:

- Run focused source-label/source drawer tests.
- Run holdings source-label tests.
- Run `git diff --check` and ruff for changed Python/TypeScript files.
