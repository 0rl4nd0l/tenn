# Extraction AAU Canary Failure Gold Fixture V1

## Summary

- Related issue: #96
- Branch: `safe/extraction-aau-canary-gold-fixture-v1-20260529`
- Worktree: `/home/l4nd0/tenn-aau-canary-gold-fixture-v1-20260529`
- Base HEAD: `d55a515376e2bd065be9c94843d07ccca06f99f2`
- Mode: SAFE EXTENSION
- Runtime extraction run: no
- Third canary run: no
- Broad backfill run: no
- Direct SQL/Qdrant/news/memory mutation: no
- Source PDF mutation/copy/staging: no
- Parser routing, prompt, schema, runtime/model/GPU/service changes: no

## Source Verification

The AAU source PDF is available locally at:

`/data/asx/docs/AAU/financial_performance/2026-03-31_annual-report-and-full-year-statutory-accounts_508fc892-ae88-45ec-981f-cd9e124c8375.pdf`

Verification used `pdfinfo`, `pdftotext -layout`, `pdftoppm -png -r 120`, and
visual inspection of rendered PNG pages under `tmp/pdfs/`.

Verified context:

- `period_type=A`
- `period_end=2025-12-31`
- `currency=USD`
- `scale=units`

Verified source metrics:

- `revenue=187743`
- `np_attributable=1100860`
- `operating_cf=-854114`
- `investing_cf=301155`
- `financing_cf=4103422`
- `cash_end=3956993`

Metrics intentionally not labelled:

- `ebit`: no verified EBIT source label.
- `capex`: no verified canonical capex source label.
- `net_debt`: would require derivation, so it is excluded.
- `shares_outstanding`: not needed for this canary failure regression.

Detailed evidence is recorded in `source_verification.json`.

## Implemented

- Added `aau_a_2025-12-31_canary_regression.json` to the test-only real-gold
  fixture set under `financial-engine_v2/backend/tests/fixtures/extraction_gold/`.
- Extended the real-gold eval tests so the AAU trusted payload is accepted.
- Added a regression assertion that the historical AAU missing-period payload is
  quarantined with `context_mismatch:period_end`.
- Preserved existing CLV and CTM canary-regression behavior.

## Validation

Completed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md --repo-root .`
- `pdfinfo`, `pdftotext -layout`, `pdftoppm -png -r 120`, and rendered PNG inspection for the AAU source PDF.
- Focused AAU/canary regression tests in `test_extraction_gold_eval.py`: `5 passed`.
- Touched real-gold eval suite excluding one known unrelated source-asset path check:
  `23 passed, 1 deselected`.
- Targeted Ruff for `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`: passed.
- `py_compile` for `test_extraction_gold_eval.py`: passed.
- JSON validation for the fixture, source-verification report, and status artifact: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Source PDF/rendered-image staging check: no staged PDF, source-data, or PNG paths.
- Staged credential scan: no hits.
- Post-change code-reviewer pass: no critical findings, warnings, or suggestions.

Known unrelated validation gap:

- The full `test_extraction_gold_eval.py` file still fails
  `test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`
  because the pre-existing 10X source PDF is not present at the repo-relative
  `financial-engine_v2/data/asx/docs/...` path. This task did not copy or stage
  source PDFs by design.

## Next Safe Step

After the AAU period-semantics code branch and this fixture branch are integrated
into the active baseline and the live backend is verified to serve the new code,
rerun AAU alone through the approved single-document canary path. Continue the
remaining #96 third-canary sequence only if AAU passes the extraction gate.
