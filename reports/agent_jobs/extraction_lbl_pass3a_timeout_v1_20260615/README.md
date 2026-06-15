# Extraction LBL Pass3a Timeout Follow-Up

Status: DONE_WITH_RISK

## Result

No code change was made. The targeted LBL canary that failed in PR #346 with
`validation_gate:insufficient_metrics:0` passed when run with the existing
supported serial extraction mode:

```text
EXTRACTION_PARALLEL=0
```

The successful canary returned:

- `status`: `ok`
- `period_end`: `2025-12-31`
- `period_type`: `H`
- `non_null_metrics`: `7`
- `scale`: `thousands`
- `model_override`: `qwen2.5:32b`

The pass confirmed that PR #346's companion period binding remained active:
`from_period_end=2026-01-31` to `to_period_end=2025-12-31` using the same-day
LBL results announcement as the companion period source.

## Root Cause

The failure was local pass3a table LLM latency against `qwen2.5:32b`, not raw
table size and not PR #346's period binding. Subagent cache inspection found
only three small Docling tables. The useful tables were page 21
`income_statement` and page 22 `cashflow_statement`; page 22 was also weakly
selected as `balance_sheet`, adding an extra local model call.

The serial canary still logged one cashflow timeout and retry, but completed
successfully and produced seven source-table metrics.

## Subagent Evidence

Maxwell inspected pass3a control flow and found that `_extract_single_table`
returns `None` after initial and truncated retry failures; `_run_pass3a_metric_extractor`
drops `None` table results, so all-table timeout leads to zero metrics and then
`validation_gate:insufficient_metrics:0`.

Galileo inspected the cached Docling output and reconstructed pass2 table
selection. The tables are under existing row caps, so row-cap trimming alone is
not a meaningful fix for this LBL case.

## Commands

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_pass3a_timeout_v1_20260615.md
python3 scripts/agent_job_registry.py list-active --read-only
DATA_ROOT=/tmp/tenn-lbl-pass3a-timeout-canary-20260615 \
LLAMACPP_URL=http://127.0.0.1:8001 \
EXTRACTION_LLAMACPP_URL=http://127.0.0.1:11434 \
OLLAMA_URL=http://127.0.0.1:11434 \
EXTRACTION_SKIP_NARRATIVE=1 \
EXTRACTION_PARALLEL=0 \
PYTHONPATH=/home/l4nd0/tenn-lbl-pass3a-timeout-v1-20260615/financial-engine_v2/backend \
timeout 900 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python /tmp/tenn_lbl_companion_canary_runner_20260615.py
```

Raw canary log:
`reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/serial_canary.log`.

## Files Touched

- `docs/agent_tasks/extraction_lbl_pass3a_timeout_v1_20260615.md`
- `reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/README.md`
- `reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/status.json`
- `reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/validation.json`
- `reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/diff-check.json`
- `reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/serial_canary.log`

## Not Touched

- No extraction code changed.
- No tests changed.
- No DB, Qdrant, Redis, news store, source PDF, prompt, gold label, schema,
  runtime config, model config, or GPU/service config was mutated.
- PR #346's branch was not modified in place.

## Residual Risk

This validates a runtime setting for the local LBL canary. It does not prove
that parallel pass3a is healthy for `qwen2.5:32b` on this host, and it does not
remove the weak duplicate `balance_sheet` selection for page 22. A later code
change could add a bounded pass3a worker-count setting or tighten weak table
deduplication, but neither is required to fix this specific canary.
