# Real-Gold Corpus Baseline Integration

Job: `extraction_real_gold_corpus_baseline_v1_20260529`

Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`

Base audited: `migration/clean-runtime-baseline-reconstruct-v1` at
`e2029835efbd2eb6425f089d703841eb20625bf7`

Mode: SAFE EXTENSION MODE.

## Decision

Integrated the BHP #96 canary regression into the real-gold evaluation corpus
and made the real-gold source-path validation portable on the current baseline.

This moves the active extraction goal forward for item 7, but it does not
complete the full goal. Runtime canary execution remains approval-gated, issues
#96-#99 remain open, and broad accurate extraction graduation is still
unproven.

No runtime reload, canary run, `POST /api/process/document`, broad extraction,
backfill, production DB write, Qdrant/news/memory mutation, source-PDF mutation,
parser/prompt/schema change, service/GPU/model config change, Cockpit UI work,
or GitHub issue/PR mutation was performed by this task.

## What Changed

- Added
  `financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json`.
- Extended `test_extraction_gold_eval.py` so a source-backed BHP FY2025 payload
  is trusted.
- Added a regression check that the historical BHP canary payload using
  FY2024 comparative revenue `55,658,000,000` is not trusted for FY2025.
- Updated real-gold scorecard expectations from 5 trusted fixtures to 6.
- Replaced the project-root-only source asset assertion with
  `resolve_confirmed_metric_coverage_source_path()`.
- Kept raw source assets optional by default and strict only under
  `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Source Verification

Read-only local source file:

`/data/asx/docs/BHP/financial_performance/2025-08-19_bhp-appendix-4e-and-2025-annual-report_2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7.pdf`

Current-turn checks:

- `sha256sum` matched fixture `source_sha256`:
  `39e139174313295df56143a3cbd2c704eeb9783bdffb4706a083706d6b5a490a`.
- `pdfinfo` opened the file and reported a 238-page PDF.
- `resolve_confirmed_metric_coverage_source_path()` resolved the source file
  through the existing allowlisted source roots and returned `is_file=True`.
- `pdftotext -layout` showed the report period as year ended 30 June 2025 and
  the relevant table values:
  - revenue `51,262` for FY2025 and comparative `55,658` for FY2024
  - net operating cash flows `18,692`
  - net debt `12,924`

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_corpus_baseline_v1_20260529.md`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  `25 passed, 5 warnings`
- `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 ... pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py::test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_source_paths`:
  `1 passed, 5 warnings`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_metric_ontology_bridge.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  `252 passed, 5 warnings`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_extraction_gold_eval.py`:
  `All checks passed!`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `python3 -m json.tool financial-engine_v2/backend/tests/fixtures/extraction_gold/bhp_a_2025-06-30_canary_regression.json`

## Goal Impact

Improves item 7, "Build a real gold/eval corpus from canary failures", by
bringing the BHP canary failure evidence and the source-path portability fix
onto a fresh baseline branch.

The overall extraction goal remains incomplete because the third canary has not
been run under fresh approval, actual canary payloads have not been scored
through the #97 gate, issue #98 remains open for persisted metric schema
alignment, issue #99 remains open for source-PDF reviewability, and full
accurate extraction graduation has not been proven.

## Next Safe Step

Run final diff/staging gates, commit this branch, release the task-card claim,
and push the branch. After this lands, the next non-runtime-safe step is to
consolidate or supersede stale draft PRs #125-#128 so the baseline can consume
the verified corpus/source-path evidence cleanly.
