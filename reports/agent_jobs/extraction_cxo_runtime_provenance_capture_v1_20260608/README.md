# CXO Runtime Provenance Capture

## Objective

Build an exact-doc, no-write runtime provenance capture for CXO plus one
additional clean scale-known control from the fixed scale-table harness. Do not
run count-24, count-32, random samples, broad extraction, or backfill.

## Current State

`DONE_WITH_RISK`

Useful report-local provenance was captured for the two exact documents, but
actual pass3a `row_refs`, `metric_source_scales`, `metric_scale_sources`, and
full debug-capture payload remain `DATA_MISSING` under the no-write boundary.

## Exact Docs Used

- CXO `control_CXO_36e172ec`
  - document_id: `36e172ec-2650-4a9f-9ef0-a4366a3b8d31`
  - source_path: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CXO/financial_performance/2022-10-31_quarterly-activities-and-cashflow-report-30-september-2022_36e172ec-2650-4a9f-9ef0-a4366a3b8d31.pdf`
  - persisted count-24 status: `ok`, period `Q`, period_end `2022-09-30`,
    scale `thousands`, non-null metrics `5`
- NSR `control_NSR_f2240712`
  - document_id: `f2240712-9dde-41e0-88fa-29c1a0080dab`
  - source_path: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NSR/financial_performance/2022-02-25_half-year-accounts_f2240712-9dde-41e0-88fa-29c1a0080dab.pdf`
  - persisted count-24 status: `ok`, period `H`, period_end `2021-12-31`,
    scale `thousands`, non-null metrics `8`

NSR was retained as the second control because live harness evidence lists it
as an `ok` financial-report, scale-known control with `thousands` scale and 8
non-null metrics. The only higher metric-count scale-known candidate found was
WHC, but the harness classifies it as `unknown_document`, so it is not cleaner
for this exact-doc financial-report control.

## Capture Summary

- Runner: `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py`
- Runtime artifact: `runtime_provenance_capture.json`
- Common scale artifact: `common_metric_source_scale_trace.json`
- Status artifact: `status.json`
- Validation artifact: `validation.json`

The runner did not call `run_multipass_extraction`, the public
`extract_structured` cache wrapper, pass3a LLM extraction, services, DB, Qdrant,
Redis, news, memory, count runners, broad extraction, or backfill. It used the
private in-memory PyMuPDF helper only because the public parser wrapper writes
parser cache on cache misses.

Captured fields include:

- selected table labels, pages, captions, headers, first rows, and row/cell
  text candidates
- table-local scale
- same-page scale and scale snippets
- document-level scale from tables and first-page text
- persisted count-24 metric values and final scale
- `_common_metric_source_scale` input/output using the persisted count-24
  metrics with empty `metric_source_scales`
- before/after source-PDF stat and parser-cache path checks

No existing parser-cache JSON was found for either exact document in the checked
cache locations. The source PDF stats and target parser-cache paths were
unchanged after capture.

## Root Cause And Repair Decision

The two cases did not prove a shared source-bound production extraction root
cause. They did share a capture evidence gap: the persisted count-24 summaries
do not carry pass3a row refs or metric source-scale fields, and no existing
parser cache was available for a no-write debug replay.

No production repair was implemented.

## DATA_MISSING

- `existing_parser_cache_json`
- `full_pass3a_llm_outputs`
- `runtime_row_refs`
- `runtime_metric_source_scales`
- `runtime_metric_scale_sources`
- `debug_capture_full_payload`

## Files Touched

- `docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/README.md`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/runtime_provenance_capture.json`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/common_metric_source_scale_trace.json`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/status.json`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/validation.json`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/task_card_validate.log`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/capture_runtime_provenance.log`
- `reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/validation.log`

Report artifacts are under ignored `reports/`, so plain `git status` only shows
the task card unless ignored files are inspected directly.

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- backend tests and extraction prompts
- source PDFs
- parser cache directories
- DB, Qdrant, Redis, news stores, memory, production data, model/GPU/service
  config
- dirty shared checkout `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- GitHub issues or PRs

## Commands Run

- `pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all && sed -n '1,260p' AGENTS.md`
  - exit status: `0`
- `python3 scripts/agent_job_registry.py list-active --read-only`
  - exit status: `0`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md`
  - exit status: `0`
  - raw log: `logs/task_card_validate.log`
- `python3 reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py`
  - exit status: `1`
  - result: default `python3` lacked `fitz` / PyMuPDF
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py`
  - exit status: `0`
  - raw log: `logs/capture_runtime_provenance.log`
- `python3 -m py_compile reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `python3 -m json.tool reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/runtime_provenance_capture.json`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `python3 -m json.tool reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/common_metric_source_scale_trace.json`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `python3 -m json.tool reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/status.json`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `python3 -m json.tool reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/validation.json`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `git diff --check`
  - exit status: `0`
  - raw log: `logs/validation.log`
- `python3 scripts/agent_job_contract.py check-diff --no-write-report docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md`
  - exit status: `0`
  - raw log: `logs/validation.log`

## Validation Status

Validation passed for the report-local runner and artifacts:

- task card validation: passed
- registry read-only inspection: passed, `active_jobs=[]`
- runner execution with repo-family venv: passed
- `py_compile`: passed
- JSON parse checks: passed
- `git diff --check`: passed
- task-card `check-diff --no-write-report`: passed

## Unsafe Actions Avoided

- no count-24 rerun
- no count-32 run
- no random sample
- no broad extraction or backfill
- no public runtime/parser route that would write parser cache
- no pass3a LLM call
- no DB/Qdrant/Redis/news/memory mutation
- no source PDF, prompt, gold-label, runtime schema, service, model, GPU, or
  production-data mutation
- no GitHub mutation
- no edit to the dirty shared checkout

## Approvals Needed

None for this completed report-local no-write capture.

Approval would be required for any next step that runs the exact pass3a/runtime
debug route and writes parser cache, starts services, uses an LLM runtime, or
implements a production repair.

## Remaining Risk

The capture is partial. It proves selected table/page and scale context from
in-memory parsing, but it does not prove actual pass3a row refs or metric
source-scale propagation because those fields were not available without a
forbidden cache-writing/runtime route.

## Next Recommended Prompt

```text
/goal Run an approval-gated exact-doc pass3a debug replay for CXO and NSR only, allowing parser-cache writes only to an isolated disposable cache directory if the code supports it, and still forbidding DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, runtime config, service-start, broad extraction, count-24, count-32, random sample, backfill, and GitHub mutation. Capture actual pass3a outputs, row_refs, metric_source_scales, metric_scale_sources, selected table/page, and _common_metric_source_scale input/output. Implement no production repair unless the two exact docs prove the same source-bound production root cause.
```
