# Extraction Accounting Number Parse

## Objective

Implement one bounded #286 production-readiness improvement: parse common
accounting number formats emitted by pass3a before reconciliation.

## Current State

DONE_WITH_RISK pending PR review. A narrow backend code/test change exists and
focused validation passed.

## Why This Slice

Issue #286 explicitly names deterministic accounting-number parsing as missing.
The backend pass3a extraction path used `float(val)`, which drops source-bound
metric strings such as `$1.2m`, `(123)`, or `A$4.5 million` by setting them to
`None`. This is a smaller and safer child slice than the full #286 provenance
schema, and it directly improves extraction readiness without touching stores,
prompts, labels, or broad runtime paths.

## Evidence Used

- Fresh worktree:
  `/home/l4nd0/tenn-accounting-number-parse-v1-20260616`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
  `83b9950d46c100a0653d7a85b2181d07abfaa118`
- Issue #286 live state: open.
- Registry read-only: `ok=true`, `read_only=true`, `active_jobs=[]`.
- Code seam:
  `financial-engine_v2/backend/app/services/multipass_extraction.py`
  `_extract_single_table()`.

## Files Touched

- `docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/README.md`
- `reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/status.json`
- `reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/diff-check.json`

## Files Intentionally Not Touched

- DB, Qdrant, Redis, news, memory, source PDFs, gold labels, prompts, schema,
  runtime/service/model/GPU config, and production data.
- Full field-level provenance schema from #286.
- Broad extraction/backfill/count-24/count-32 paths.

## Implementation

- Added `_parse_accounting_metric_number()` for pass3a metric values.
- Parses comma-separated numbers, parentheses negatives, currency prefixes, and
  explicit suffixes: `k`, `thousand`, `m`, `mn`, `million`, `b`, `bn`,
  `billion`, `t`, `tn`, and `trillion`.
- Preserves table/document scale multiplication when values have no explicit
  unit suffix.
- Avoids double-scaling when values carry explicit unit suffixes.
- Leaves nonnumeric strings fail-closed as `None`.

## Commands Run

- `git fetch origin --prune`: exit 0.
- `gh issue view 286 --json number,title,state,labels,body,url,updatedAt`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only`: exit 0.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md`: exit 0.
- RED:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_parses_common_accounting_number_strings -q`: exit 1, failed because `revenue` was `None`.
- GREEN:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_parses_common_accounting_number_strings financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_applies_thousands_multiplier financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_negative_values_preserved financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_applies_idr_trillion_scale_without_aud_cap_fallback financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_extracts_net_debt_note -q`: exit 0, 5 passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`: exit 0.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`: exit 0.
- `git diff --check`: exit 0.
- `python3 -m json.tool reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/status.json >/dev/null && python3 -m json.tool reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/validation.json >/dev/null`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md --repo-root .`: exit 0.

## Validation Status

Focused validation passed. No broad extraction, samples, backfills, service
routes, or production mutations were run.

## DATA_MISSING

- No broad accuracy or runtime coverage claim is made.
- Full #286 field-level provenance storage remains open.

## Remaining Risk

This repairs pass3a value coercion for common accounting strings. It does not
add per-field persisted provenance, and it does not prove corpus-wide accuracy.

## Next Recommended Prompt

Review and merge the narrow #286 child PR for pass3a accounting-number parsing;
then choose the next #286 child slice: field-level source excerpt/page
provenance in payloads or persistence.
