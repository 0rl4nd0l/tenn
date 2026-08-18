# LBL Companion Period Provenance Safe Extension

Job: `extraction_lbl_companion_period_provenance_v1_20260614`

Worktree: `/home/l4nd0/tenn-lbl-companion-period-provenance-v1-20260614`

Branch: `safe/extraction-lbl-companion-period-provenance-v1-20260614`

Base HEAD: `efd11b9a44d9d73bf94b86f6d90c8f75342bb0cf`

Status: `DONE_WITH_RISK`

## Scope

Implemented the approved narrow LBL companion-source period binding rule. The rule is limited to half-year payloads where the target document only has label/title context and the current `period_end` is the leading announcement date. It may bind `period_end` only from explicit same-day, same-ticker companion source text.

Accepted companion roles:

- `appendix4d`
- `half_year_financial_report`
- `results_announcement`

Rejected or fail-closed cases:

- target document already has same-document exact source-text period evidence
- title-only, filename-only, publication-date-only, or loose date evidence
- non-half-year payloads
- companion sources from another ticker, date, or category
- disagreement between eligible companion source period ends
- unrecognized generic companion roles

Scale behavior is unchanged: target table-local scale still wins. Companion document scale is not copied into the target payload.

## Files Touched

- `docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/README.md`
- `reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/status.json`
- `reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/validation.json`
- `reports/agent_jobs/extraction_lbl_companion_period_provenance_v1_20260614/diff-check.json`

All touched files are inside the validated task-card allowlist.

## Implementation Notes

- Added `_bind_companion_source_period_end_over_announcement_date`.
- Added same-day/same-ticker/category path checks for ASX document siblings.
- Added narrow companion PDF text discovery for runtime use. Discovery only scans the target PDF's immediate directory and reads candidate companion PDFs with `pdftotext` pages 1-4 when available. Missing `pdftotext`, timeout, unreadable PDFs, or no exact phrase fail closed.
- Added cross-document provenance into `_source_period_end_binding`, including `target_source_path`, `period_source_path`, `period_source_role`, `selection_rule`, and `corroborating_source_paths`.
- Propagated companion evidence into pass-4 payload source period evidence.
- Added focused tests for successful LBL Appendix 4D binding and companion disagreement fail-closed behavior.
- Added debug-level diagnostics for companion PDF text discovery fail-closed paths.
- Added a focused synthetic discovery test for same-day same-ticker companion role filtering.
- After the live LBL canary showed pass1 could emit unsupported `2026-01-31`,
  broadened the companion binder to override unsupported pass1 dates when exact
  same-day companion evidence agrees. Same-document source binding remains
  restricted to announcement-title-date conflicts.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md`
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- dependency-stubbed direct runner for 10 focused period-end tests in `test_extraction_pre_canary_truth_gates.py`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/.local/bin/uv run --with 'pytest>=8.3.3' --with 'pytest-asyncio>=0.24.0' --with 'pydantic==2.9.2' --with 'pydantic-settings==2.6.1' --with 'python-dateutil==2.9.0.post0' --with 'fastapi==0.115.6' --with 'sqlalchemy==2.0.36' --with 'httpx==0.27.2' --with 'numpy==1.26.4' --with 'pymupdf==1.24.10' --with 'beautifulsoup4==4.12.3' --with 'lxml==5.3.0' pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -k 'period_end or companion'`
  - result: `11 passed, 15 deselected in 0.23s`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/.local/bin/uv run --with 'pytest>=8.3.3' --with 'pytest-asyncio>=0.24.0' --with 'pydantic==2.9.2' --with 'pydantic-settings==2.6.1' --with 'python-dateutil==2.9.0.post0' --with 'fastapi==0.115.6' --with 'sqlalchemy==2.0.36' --with 'httpx==0.27.2' --with 'numpy==1.26.4' --with 'pymupdf==1.24.10' --with 'beautifulsoup4==4.12.3' --with 'lxml==5.3.0' pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - result: `26 passed in 0.66s`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/.local/bin/uv run --with 'pytest>=8.3.3' --with 'pytest-asyncio>=0.24.0' --with 'pydantic==2.9.2' --with 'pydantic-settings==2.6.1' --with 'python-dateutil==2.9.0.post0' --with 'fastapi==0.115.6' --with 'sqlalchemy==2.0.36' --with 'httpx==0.27.2' --with 'numpy==1.26.4' --with 'pymupdf==1.24.10' --with 'beautifulsoup4==4.12.3' --with 'lxml==5.3.0' pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - result after reviewer follow-up: `27 passed in 0.23s`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/.local/bin/uv run --with 'pytest>=8.3.3' --with 'pytest-asyncio>=0.24.0' --with 'pydantic==2.9.2' --with 'pydantic-settings==2.6.1' --with 'python-dateutil==2.9.0.post0' --with 'fastapi==0.115.6' --with 'sqlalchemy==2.0.36' --with 'httpx==0.27.2' --with 'numpy==1.26.4' --with 'pymupdf==1.24.10' --with 'beautifulsoup4==4.12.3' --with 'lxml==5.3.0' pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - result after live-canary regression: `28 passed in 0.20s`
- Targeted LBL canary:
  - command shape: `DATA_ROOT=/tmp/tenn-lbl-companion-canary-20260615 LLAMACPP_URL=http://127.0.0.1:8001 EXTRACTION_LLAMACPP_URL=http://127.0.0.1:11434 OLLAMA_URL=http://127.0.0.1:11434 EXTRACTION_SKIP_NARRATIVE=1 PYTHONPATH=<current backend> timeout 900 <baseline venv python> /tmp/tenn_lbl_companion_canary_runner_20260615.py`
  - source PDF: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/financial_performance/2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf`
  - result: `status=failed`, `error=validation_gate:insufficient_metrics:0`, `period_type=H`, `period_end=2025-12-31`, `source_period_end_binding.reason=explicit_companion_source_half_year_period_end_over_unsupported_pass1_period_end`
  - interpretation: the period provenance fix worked in runtime, but local Ollama `qwen2.5:32b` timed out in pass3a table extraction and produced zero metrics.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_lbl_companion_period_provenance_v1_20260614.md`

Not run:

- no broad extraction, count, backfill, service, DB, Qdrant, Redis, news, model, GPU, or runtime validation was run.

## Safety

The dirty baseline checkout at `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` was preserved. No merge, rebase, reset, stash, clean, GitHub write, source PDF edit, prompt edit, production data mutation, or runtime service start was performed.

## Residual Risk

Runtime discovery depends on `pdftotext` being available where extraction runs. The approved targeted canary proved the period binding path but did not prove full metric extraction because local pass3a LLM calls timed out and the gate failed on `insufficient_metrics:0`.
