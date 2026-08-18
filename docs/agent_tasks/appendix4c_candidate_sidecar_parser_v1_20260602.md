---
job_id: appendix4c_candidate_sidecar_parser_v1_20260602
lane: Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md
  - financial-engine_v2/backend/app/services/asx_appendix4c_parser.py
  - financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py
  - reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/README.md
  - reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/status.json
  - reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/validation.json
  - reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/diff-check.json
  - reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602/code_review.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/appendix4c_candidate_sidecar_parser_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Appendix 4C Candidate Sidecar Parser v1

## Summary

Implement the bounded Appendix 4C candidate sidecar parser child from GitHub issue #72.
The parser must operate only on caller-provided structured table rows and return
report-local candidate evidence. It must not route production extraction, write
canonical financial truth, call runtime/model services, or mutate source/data stores.

## Lane Declaration

Lane: Financial Truth
Supporting lanes: Evaluation, Provenance
Execution mode: SAFE EXTENSION MODE
Worktree: `/home/l4nd0/tenn-appendix4c-candidate-sidecar-parser-v1-20260602`
Branch: `safe/appendix4c-candidate-sidecar-parser-v1-20260602`
Collision risk: HIGH by issue class, reduced to MEDIUM only for this isolated
sidecar because no active registry job owns the exact files and no open PR
currently owns an Appendix 4C parser implementation.

## Scope

Allowed:
- Add a standalone `asx_appendix4c_parser.py` service module.
- Add focused unit tests for parsing explicit Appendix 4C cash-flow lines.
- Record validation/report artifacts under this job output directory.

Forbidden:
- production parser routing
- Docling config
- extraction prompts
- canonical financial truth writes
- source PDFs or raw filing bundles
- DB/Qdrant/news/memory writes
- production data access
- runtime/model/GPU/service config
- gold labels
- Cockpit product/runtime behavior

## Parser Contract

- Input: already-extracted structured table rows supplied by the caller.
- Output: in-memory candidate parse result only.
- `canonical_write=false` at result and candidate level.
- No LLM calls.
- No runtime calls.
- No persistence.
- No production routing imports.
- Missing or ambiguous evidence returns `DATA_MISSING`, never zero or substituted values.

Candidate line items:
- `1.1` receipts from customers: `cash_receipts`, `review_only`, not revenue.
- `1.9` net operating cash flow: `operating_cf`, candidate.
- `2.6` net investing cash flow: `investing_cf`, candidate.
- `3.10` net financing cash flow: `financing_cf`, candidate.
- `4.6` or `5.5` cash at end of period: `cash_end`, candidate.

Unsupported metrics that must never become Appendix 4C candidates:
- revenue
- NPAT / net profit after tax
- EBIT / EBITDA
- net debt
- shares outstanding
- income-statement, balance-sheet, EPS, NTA, dividends, margin, ratio, or segment metrics

## Validation

Required commands:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/asx_appendix4c_parser.py financial-engine_v2/backend/tests/test_asx_appendix4c_parser.py`
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/services/asx_appendix4c_parser.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/appendix4c_candidate_sidecar_parser_v1_20260602.md`
- `python3 scripts/agent_job_registry.py release appendix4c_candidate_sidecar_parser_v1_20260602`

## Hard Stops

Stop if:
- active registry overlap owns the exact files;
- an open PR owns an Appendix 4C parser implementation;
- implementation requires production routing or canonical writes;
- tests require changing source labels, extraction prompts, gold labels, canonical truth, runtime/model config, source PDFs, or production data;
- the parser cannot keep current-quarter and year-to-date evidence separate.

## Definition Of Done

- Task-card validate/check-overlap/claim/check-diff/release pass.
- Focused parser tests pass.
- Comparator artifact schema tests still enforce Appendix 4C forbidden metric boundaries.
- Parser outputs explicit candidates only from line-item evidence.
- Missing lines are `DATA_MISSING`.
- Production routing files do not import the Appendix 4C parser.
- No forbidden surfaces are changed.
