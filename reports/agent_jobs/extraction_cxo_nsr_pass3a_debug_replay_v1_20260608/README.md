# CXO/NSR Pass3a Debug Replay

## Objective

Run an approval-gated exact-doc pass3a debug replay for CXO and NSR only,
allowing parser-cache writes only to an isolated disposable cache directory if
supported. Do not run count-24, count-32, random samples, broad extraction,
backfill, services, or any production data mutation.

## Current State

`DONE_WITH_RISK`

The exact-doc replay succeeded on the second bounded attempt and captured the
requested pass3a provenance fields for both documents. Risk remains because
task-card `check-diff` is blocked by a preserved pre-existing untracked task
card from the previous approved step, and the first bounded attempt wrote one
isolated `/tmp` router metrics snapshot before router metrics persistence was
disabled for the successful replay.

## Exact Docs Used

- CXO `control_CXO_36e172ec`
  - document_id: `36e172ec-2650-4a9f-9ef0-a4366a3b8d31`
  - source_path: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CXO/financial_performance/2022-10-31_quarterly-activities-and-cashflow-report-30-september-2022_36e172ec-2650-4a9f-9ef0-a4366a3b8d31.pdf`
  - replay status: `ok`
- NSR `control_NSR_f2240712`
  - document_id: `f2240712-9dde-41e0-88fa-29c1a0080dab`
  - source_path: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NSR/financial_performance/2022-02-25_half-year-accounts_f2240712-9dde-41e0-88fa-29c1a0080dab.pdf`
  - replay status: `ok`

## Isolated Cache

Current code does not expose a per-call parser cache directory, but
`docling_extract.py` derives the parser cache root from process-local
`DATA_ROOT` at backend import time. The cache-support probe verified this path
without writing production cache:

- probe root: `/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-probe`
- successful replay root: `/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608133053`
- successful replay cache root: `/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608133053/reports/extraction_cache/docling_extract`

The successful replay wrote exactly two isolated Docling cache files under that
cache root. Validation confirmed the normal parser cache paths and source PDF
stats were unchanged.

## Pass3a Capture Summary

Requested fields captured: pass3a outputs, `row_refs`,
`metric_source_scales`, `metric_scale_sources`, selected table/page, and
`_common_metric_source_scale` input/output.

CXO:

- pass3a tables: `cashflow_statement` page 14, `share_capital` page 8
- row refs captured for `operating_cf`, `investing_cf`, `financing_cf`,
  `capex`, `cash_end`, and `shares_outstanding`
- metric source scales: all captured as `thousands`
- scale sources: cash-flow metrics from `table`, shares from `document`
- final scale: `thousands`

NSR:

- pass3a tables: `cashflow_statement` page 12, `income_statement` page 8,
  `balance_sheet` page 10, `share_capital` page 24
- row refs captured for `revenue`, `ebit`, `operating_cf`, `capex`,
  `cash_end`, `financing_cf`, `investing_cf`, `net_debt`, and
  `shares_outstanding`
- metric source scales: table/document source scales captured as `thousands`
- scale sources: table for financial metrics, document for shares
- final scale: `thousands`

`_common_metric_source_scale` traces:

- CXO input metric scales all `thousands`, fallback `thousands`, output
  `thousands`
- NSR input metric scales all `thousands`, fallback `thousands`, output
  `thousands`

## Root Cause And Repair Decision

The two exact docs did not prove the same source-bound production root cause.
Both documents now show explicit pass3a source-scale propagation and common
scale output `thousands`; the replay does not identify a shared production
defect requiring repair.

No production repair was implemented.

## DATA_MISSING

None for the requested replay fields.

## Files Touched

- `docs/agent_tasks/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608.md`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/README.md`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.py`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.json`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/common_metric_source_scale_trace.json`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/status.json`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/validation.json`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/task_card_validate.log`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/cache_support_probe.log`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/pass3a_debug_replay.log`
- `reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/validation.log`

Report artifacts are under ignored `reports/`, so plain `git status` does not
show them unless ignored files are included.

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- extraction prompts and gold labels
- source PDFs
- normal parser-cache directories
- DB, Qdrant, Redis, news stores, memory, production data, model/GPU/service
  config
- dirty shared checkout `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- GitHub issues or PRs

## Commands Run

- `pwd -P && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all`
  - exit status: `0`
- `python3 scripts/agent_job_registry.py list-active --read-only`
  - exit status: `0`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608.md`
  - exit status: `0`
  - raw log: `logs/task_card_validate.log`
- `DATA_ROOT=/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-probe PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python - <cache support probe>`
  - exit status: `0`
  - raw log: `logs/cache_support_probe.log`
- `DATA_ROOT=/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608132618 PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.py`
  - exit status: `0`
  - result: first bounded attempt failed before pass3a with `OLLAMA_URL must be set when provider is 'ollama'`
  - raw log: `logs/pass3a_debug_replay.log`
- `PYTHONDONTWRITEBYTECODE=1 DATA_ROOT=/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608133053 PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.py`
  - exit status: `0`
  - result: requested fields captured for CXO and NSR
  - raw log: `logs/pass3a_debug_replay.log`
- `python3 -m json.tool` on replay, common trace, status, and validation JSON
  - exit status: `0`
- `jq -e '(.source_pdf_before == .source_pdf_after) and (.normal_cache_before == .normal_cache_after)' pass3a_debug_replay.json`
  - exit status: `0`
- `jq -e '<requested field capture predicate>' status.json`
  - exit status: `0`
- `test "$(find /tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608133053 -type f ! -path "*/reports/extraction_cache/docling_extract/*.docling.json" | wc -l)" -eq 0`
  - exit status: `0`
- `git diff --check`
  - exit status: `0`
- `python3 scripts/agent_job_contract.py check-diff --no-write-report docs/agent_tasks/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608.md`
  - exit status: `1`
  - result: failed only because preserved pre-existing `docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md` is outside this task card allowlist

## Validation Status

Passed:

- task-card validation
- registry read-only inspection, `active_jobs=[]`
- isolated cache support probe
- successful exact-doc replay
- JSON parse checks
- requested-field capture check
- source PDF and normal parser-cache unchanged check
- successful replay `/tmp` parser-cache-only check
- `git diff --check`

Known validation caveat:

- task-card `check-diff` failed because of preserved pre-existing untracked
  prior task card dirt outside this job's exact allowlist.

## Unsafe Actions Avoided

- no count-24 rerun
- no count-32 run
- no random sample
- no broad extraction or backfill
- no normal parser-cache write
- no DB/Qdrant/Redis/news/memory write
- no source PDF, prompt, gold-label, runtime config, service, model, GPU, or
  production-data mutation
- no service start
- no GitHub mutation
- no production repair

## Remaining Risk

The replay used process-local `DATA_ROOT`, `LLAMACPP_URL`,
`EXTRACTION_LLAMACPP_URL`, and `OLLAMA_URL` defaults inside the bounded runner
only. These were not written to repo config or service config.

The first bounded attempt wrote an isolated
`/tmp/tenn-pass3a-debug-replay-cache-v1-20260608-run-20260608132618/reports/router_metrics_snapshot.json`
before metrics persistence was disabled. The successful second attempt wrote
only the two isolated parser-cache files under its disposable cache root.

## Next Recommended Prompt

```text
/goal Review the CXO/NSR pass3a debug replay artifacts and decide whether any follow-up issue is needed for the report-local replay harness itself. Do not implement extraction production repair unless new exact-doc evidence proves a repeated source-bound production root cause outside these clean controls.
```
