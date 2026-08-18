#96 blocker fix implemented in `safe/extraction-pymupdf-cache-source-readonly-fix-v1-20260527`.

Report: `reports/agent_jobs/extraction_pymupdf_cache_source_readonly_fix_v1_20260527/README.md`

Change: `docling_extract.py` now writes Docling/PyMuPDF extraction cache files under `<settings.data_root>/reports/extraction_cache/docling_extract/` with deterministic source-metadata keys instead of writing `.pymupdf.json` sidecars beside source PDFs.

Validation: focused `test_docling_extract.py` passed (`17 passed`), py_compile passed, ruff passed, `git diff --check` passed, and no `.pdf` paths were staged.

No extraction canary, backfill, DB writes, Qdrant/news/memory mutation, source PDF edits, service restart, or runtime/model/GPU config change was run.

Remaining DATA_MISSING: live backend loaded code version was not checked; `.cursor/rules/*` architecture-check files are absent; the canary README is missing in this isolated worktree but was read from the sibling approval-packet worktree.
