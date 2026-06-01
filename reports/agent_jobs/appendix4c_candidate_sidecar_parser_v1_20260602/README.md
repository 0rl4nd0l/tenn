# Appendix 4C Candidate Sidecar Parser v1

## Summary

This job implements the bounded GitHub issue #72 child slice: a standalone
Appendix 4C candidate parser over caller-provided structured table rows.

The parser is report-local and candidate-only. It does not route production
extraction, write canonical financial truth, call LLM/runtime services, mutate
source PDFs, or access production DB/Qdrant/news/memory stores.

## Scope

Changed files:
- `financial-engine_v2/backend/app/services/asx_appendix4c_parser.py`
- `financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py`
- `docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/*`

## Behavior

Candidate line items:
- `1.1` receipts from customers -> `cash_receipts`, `review_only`, never `revenue`
- `1.9` net operating cash flow -> `operating_cf`, `candidate`
- `2.6` net investing cash flow -> `investing_cf`, `candidate`
- `3.10` net financing cash flow -> `financing_cf`, `candidate`
- `4.6` / `5.5` cash at end of period -> `cash_end`, `candidate`

Guardrails:
- `canonical_write` is false on the parse result and every candidate.
- Current-quarter and year-to-date columns stay separate.
- Missing lines produce `DATA_MISSING` records instead of zeroes.
- Appendix 5B rows are not parsed as Appendix 4C.
- Production routing files do not import the new sidecar parser.

## Validation

Passed:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
  - `24 passed`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/asx_appendix4c_parser.py financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/asx_appendix4c_parser.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `python3 scripts/agent_job_registry.py release appendix4c_candidate_sidecar_parser_v1_20260602`
- `python3 scripts/agent_job_registry.py list-active`
  - `active_jobs: []`

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md`
- `.cursor/rules/00_mandatory_index.md`
- `.cursor/rules/backend_architecture.md`
- `.cursor/rules/embedding_rules.md`
- `.cursor/rules/vector_store_invariants.md`
- `.cursor/rules/failure_policy.md`
- `reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/README.md`
- `reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/parser_readiness_map.json`
- `reports/agent_jobs/appendix4c_deterministic_sidecar_parser_prototype_v1/fixture_gate_proposal.json`

## Boundary Compliance

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No source PDF mutation.
- No runtime/model/GPU/service config mutation.
- No Cockpit UI/runtime behavior change.
