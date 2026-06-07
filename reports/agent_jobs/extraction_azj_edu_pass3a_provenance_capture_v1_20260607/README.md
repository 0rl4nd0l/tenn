# AZJ/EDU Pass 3a Provenance Capture

State: DONE_WITH_RISK

This report captures exact-document AZJ and EDU Pass 3a / multipass provenance
after the selected-table diagnostic. It is no-write with respect to DB, Qdrant,
Redis, news stores, memory, source PDFs, prompts, gold labels, schema, runtime
config, model config, GPU config, and production data.

## Objective

Determine whether AZJ and EDU prove the same selected-table scale propagation
root cause. Implement no code unless both documents prove the same narrow,
source-bound missed propagation path.

## Constraints

- No count-24 rerun.
- No count-32.
- No random sample.
- No broad extraction or backfill.
- No source-PDF edits.
- No prompt, gold-label, schema, runtime-config, model-config, or GPU-config
  changes.

## Current Evidence

- Diagnostic commit replayed: `a24d0d9a`
- Original diagnostic commit: `1a1b1c2a7d7fec23d420a509b44dc5d18b59e0fb`
- Count-24 artifact root:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/`
- Scale evidence artifact root:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/`

## Diagnostic Integration Result

The selected-table diagnostic commit
`1a1b1c2a7d7fec23d420a509b44dc5d18b59e0fb` was replayed cleanly onto current
canonical as `a24d0d9a`. The replay was add-only report/task content and the
diagnostic task card validated successfully.

## Capture Route

The capture runner used exact AZJ/EDU source paths from the count-24 artifacts
and loaded exact parser-cache JSON from the count-24 worktree. It patched the
parser call in memory so `run_multipass_extraction(...)` used the cached
structured document without parser-cache writes. It ran no sample selection,
count-24 rerun, count-32, broad extraction, or backfill.

Runtime used:

- interpreter:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python`
- LLM route: existing local `http://127.0.0.1:8001`
- extraction model env: `model:qwen2.5-14b-instruct`

## AZJ/EDU Provenance Table

| Doc | Result | Selected pages | Table-local scale | Same-page scale | Runtime row refs | Runtime metric source scale | `_common_metric_source_scale` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` | `failed`, `validation_gate:scale_unknown` | income p9, balance p11, cash flow p13, highlights p16, share capital p39 | `unknown` for selected tables | `millions` on income/balance/cash/share pages; `unknown` highlights | present for revenue, EBIT, NPAT, operating CF, investing CF, financing CF, capex, cash, net debt, shares | `DATA_MISSING` for all metrics because selected table scale stayed unknown | input metric scales `{}`, fallback `unknown`, output `unknown` |
| EDU `ac3c9ab0-e01a-4996-95f9-6466388ddc9c` | `failed`, `validation_gate:scale_unknown` | income p6, balance p51, cash flow p53, highlights p7, share capital p44 | `unknown` for selected tables | `units` on balance/cash-flow pages; `unknown` income/highlights/share-capital | present for revenue and cash-flow metrics only | `DATA_MISSING` for all metrics because selected table scale stayed unknown | input metric scales `{}`, fallback `unknown`, output `unknown` |

Source paths:

- AZJ:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/AZJ/financial_performance/2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf`
- EDU:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/EDU/financial_performance/2024-02-27_2023-annual-report_ac3c9ab0-e01a-4996-95f9-6466388ddc9c.pdf`

## Root-Cause Decision

Same root cause proven: no.

AZJ and EDU both end with empty `metric_source_scales`, but the source evidence
does not support one shared repair:

- AZJ selected statement pages carry same-page `millions` evidence.
- EDU balance/cash-flow pages carry raw-dollar `units` evidence, while the
  selected income/highlight/share-capital surfaces are mixed or unclean.
- No table-local scale marker was found on either document's selected tables.
- The exact Pass 3a outputs were captured, but Pass 4 had no per-metric scale
  labels to propagate.

No production extraction code repair was made.

## Final Decision

`NEEDS_SCALE_TABLE_HARNESS`

The next safe step is a focused harness around selected-table page scale
evidence and per-metric scale propagation, with EDU's mixed/unclean selected
surfaces kept explicit. Count-24 rerun is not justified from this evidence.
Count-32 remains blocked.

## DATA_MISSING

- No per-metric source scale labels were produced for AZJ or EDU.
- No selected-table table-local scale markers were found.
- EDU clean formal income-statement selection remains unproven.
- Source-bound policy for AZJ nearest-$100k rounding remains outside this task.

## Files Touched

- `docs/agent_tasks/extraction_azj_edu_pass3a_provenance_capture_v1_20260607.md`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/README.md`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/capture_runner.py`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/status.json`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/raw_commands.log`
- `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/validation.json`

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- source PDFs
- DB, Qdrant, Redis, news stores, memory, prompts, gold labels, schema, runtime
  config, model config, and GPU config

## Validation Status

- Diagnostic task-card validate: pass.
- AZJ/EDU task-card validate: pass.
- Exact-doc capture runner: pass with baseline venv Python.
- JSON validation for generated status/provenance artifacts: pass.
- `py_compile` for report-local runner: pass.
- `ruff` for report-local runner through baseline venv: pass.
- `git diff --check`: pass before staging.
- Registry read-only check: pass, `read_only=true`, `active_jobs=[]`.
- Final staged check-diff and source-PDF staged checks are recorded in the final
  closeout commands.

## Unsafe Actions Avoided

- Did not rerun count-24.
- Did not run count-32.
- Did not run random sample selection.
- Did not run broad extraction, broad backfill, or full ticker-universe
  extraction.
- Did not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schema, runtime config, model config, or GPU config.

## Next Recommended Prompt

```text
/goal Build a focused selected-table scale harness for AZJ/EDU-class failures. Use the exact captured provenance in reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/. Do not run count-24/count-32/random samples/backfill. Prove whether selected same-page scale evidence can be source-bound into per-metric metric_source_scales without loosening truth gates, and keep EDU locator/parser-table ambiguity fail-closed.
```
