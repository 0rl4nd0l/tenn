# Extraction Canary Advisory Candidate Exclusion

Date: 2026-05-29
Job: `extraction_canary_advisory_candidate_exclusion_v1_20260529`
Lane: Financial Truth
Supporting lanes: Query Orchestration, Provenance, Evaluation
Mode: SAFE EXTENSION

## Verdict

Advisory-only document blocking is now moved upstream into the #96 terminal
extraction candidate manifest path. Records whose title or first-page metadata
matches the shared advisory-only document gate are excluded before normal
candidate classification and are emitted under `excluded_candidates` with
`exclusion_reason=advisory_only_document`.

The existing PR #125 multipass guard remains in place as the second safety net.
No canary, extraction batch, broad backfill, DB write, direct SQL mutation,
Qdrant/news/memory mutation, source PDF edit, parser routing change, extraction
prompt change, gold-label mutation, runtime/model/GPU config change, service
restart, schema migration, or Cockpit UI work was performed.

## Where The Selector Changed

- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
  now checks each input record in `build_terminal_extraction_candidate_manifest()`
  with the shared advisory-only predicate before calling
  `classify_terminal_extraction_candidate()`.
- Advisory records are not placed in `manifest["candidates"]` and therefore do
  not contribute to `canary_candidate` or `retry_candidate` action counts.
- Advisory records are emitted as explicit quarantine/exclusion evidence:
  - `candidate_document_count`
  - `excluded_document_count`
  - `exclusion_reason_counts`
  - `exclusion_reason_definitions`
  - `excluded_candidates`

## Shared Backstop

`financial-engine_v2/backend/app/services/multipass_extraction.py` now exposes
the existing advisory-only predicate as `is_advisory_only_document()` so the
selector and the multipass pre-persistence guard use the same match logic.

The pattern now covers both:

- `Quarterly Report Advisory`
- `Quarterly Activities Report Advisory`

## Proof

Focused tests added in
`financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
prove:

- a `March 2026 Quarterly Activities Report Advisory` record does not enter
  `manifest["candidates"]`;
- the excluded record is emitted with
  `exclusion_reason=advisory_only_document`;
- a normal financial-report record still enters the manifest as a canary
  candidate;
- first-page text alone can trigger the advisory exclusion;
- advisory exclusions do not increment the `file_exists_no_current_terminal_run`
  or `canary_candidate` counts.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -k 'terminal_candidate_manifest or terminal_extraction_candidate'`
  - `5 passed, 20 deselected`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -k advisory`
  - `1 passed, 6 deselected`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - `32 passed`
- `uv run --no-project --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `git diff --check`
- `python3 -m json.tool reports/agent_jobs/extraction_canary_advisory_candidate_exclusion_v1_20260529/status.json`
- raw PDF/source-data staging check
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_canary_advisory_candidate_exclusion_v1_20260529.md --repo-root .`

Code-review pass: no remaining critical, warning, or suggestion findings after
preserving `total_document_count` as the input-record count and adding
`candidate_document_count` for post-exclusion candidate rows.

## Remaining DATA_MISSING

- `.cursor/rules/` architecture rule files are absent in this checkout.
- No third #96 canary was run by instruction, so live canary outcome remains
  pending explicit approval.
- Raw-dollar scale policy remains unresolved.
- Non-AUD/Rp trillion policy remains unresolved.
- Global `ok_low_confidence` surfacing policy remains report-only.

## Files Intentionally Not Touched

- DB, Qdrant, news, memory, and canonical financial truth stores.
- Source PDFs.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime/model/GPU config.
- Persisted schemas and Alembic migrations.
- Cockpit UI.
