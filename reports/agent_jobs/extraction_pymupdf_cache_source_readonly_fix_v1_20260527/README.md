# #96 PyMuPDF Cache Source Read-Only Fix - 2026-05-27

## Outcome

Status: FIX IMPLEMENTED AND VALIDATED.

Worktree:
`/home/l4nd0/tenn-extraction-pymupdf-cache-source-readonly-fix-v1-20260527`

Branch:
`safe/extraction-pymupdf-cache-source-readonly-fix-v1-20260527`

Starting HEAD:
`c275e3c857cadd8c88491b38c13a3af6debe2539`

Task card:
`docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md`

## Root Cause

Confirmed. The #96 canary report in the sibling approval-packet worktree says
both submitted documents failed because PyMuPDF fallback attempted to write
`.pdf.pymupdf.json` beside source PDFs under read-only `/data/asx/docs`.

The source path write was present in `docling_extract.py` through direct
`Path(pdf_path + ".pymupdf.json")` cache writes on PyMuPDF fallback paths.

## Change

`docling_extract.py` now resolves extraction cache files under:

`<settings.data_root>/reports/extraction_cache/docling_extract/`

Cache filenames are deterministic and include:

- SHA-256 over source path, source file size, and source file mtime where
  metadata is available.
- A sanitized source filename label.
- The existing `.docling.json` or `.pymupdf.json` suffix.

The resolver checks that generated cache paths remain under the approved cache
root. `_save_cache()` now creates the cache parent directory before writing.

## Source PDF Safety

Source PDFs remain read-only inputs. The parser no longer writes PyMuPDF cache
sidecars next to source PDFs, and tests assert no `*.pdf.pymupdf.json` source
sidecar is created. Docling cache writes are also routed through the same
approved cache root so a successful Docling extraction does not fail merely
because `/data/asx/docs` is read-only.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md`
  - PASS
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md --repo-root .`
  - PASS
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pymupdf_cache_source_readonly_fix_v1_20260527.md --repo-root .`
  - PASS
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_docling_extract.py -q`
  - PASS: `17 passed in 0.28s`
  - Final repeat PASS: `17 passed in 0.25s`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/docling_extract.py financial-engine_v2/backend/tests/test_docling_extract.py`
  - PASS
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/docling_extract.py financial-engine_v2/backend/tests/test_docling_extract.py`
  - PASS: `All checks passed!`
- `git diff --check`
  - PASS
- No `.pdf` files staged
  - PASS

## Canary Retry Readiness

A fresh #96 canary retry is safe to request after this commit is integrated
into the live backend/worker runtime. This task did not restart services and
did not run another canary, so retry readiness still requires normal operator
approval and live-runtime loaded-code confirmation.

## Remaining DATA_MISSING

- The canary README was `DATA_MISSING` in this isolated worktree at
  `reports/agent_jobs/extraction_primary_canary_run_v1_20260527/README.md`;
  the sibling approval-packet worktree report was read as supporting evidence.
- Repo-local `.cursor/rules/*` files required by the architecture-check skill
  are missing; `SYSTEM_CONTRACT.md`, `docs/entrypoints.md`, and
  `docs/architecture/13_security_and_secrets.md` were used as fallback
  compliance sources.
- Live backend loaded code version was not checked because service restart or
  runtime mutation is forbidden for this task.

## Registry

Registry claim for this task was active during the implementation, then
released. Final `list-active` showed an unrelated PR39 Evaluation job with no
file overlap; details are recorded in `status.json`.

## Project Memory Recommendation

Save that #96's canary blocker was fixed by routing Docling/PyMuPDF extraction
cache files to `<DATA_ROOT>/reports/extraction_cache/docling_extract/` instead
of source-PDF sidecars, with no extraction/backfill run.
