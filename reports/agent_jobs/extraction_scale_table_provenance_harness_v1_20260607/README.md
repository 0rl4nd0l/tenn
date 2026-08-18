# Scale-Table Provenance Harness

State: DONE_WITH_RISK

## Objective

Build a fixed regression/provenance harness for scale-table source binding from
current count-24 failures and prior diagnostics, then identify the next safe
repair path without rerunning count-24, count-32, random samples, broad
extraction, or backfill.

## Current State

The harness is built and validated as a no-extraction evaluation artifact.

- Harness manifest:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/harness_manifest.json`
- Evidence table:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/evidence_table.json`
- Root-cause grouping:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/root_cause_grouping.json`
- Repair decision:
  `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/repair_decision.json`

The code path is
`python3 financial-engine_v2/scripts/broad_extraction_test.py --scale-table-provenance-harness`.
It returns before PDF discovery, LLM client creation, sample selection, parser
execution, or extraction.

## Evidence Used

- PR #319 merge commit:
  `07bdfe6d84eeba41c357eaf5893420ef77189625`.
- PR #319 merged state from `gh pr view 319`.
- Selected-table diagnostic:
  `reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/`.
- AZJ/EDU pass3a provenance capture:
  `reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/`.
- External read-only count-24 bounded-validation artifacts:
  `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/`.
- Prior count-24 failure taxonomy read from git history only:
  `b5537f933f2b7b31a1cab8dea0f4204ba2ac8360`.

## Harness Cases

| Ticker | Role | Expected status/gate |
| --- | --- | --- |
| AZJ | same-page scale candidate | `validation_gate:scale_unknown` |
| EDU | mixed selected surfaces | `validation_gate:scale_unknown` |
| WHC | parser/table coverage gap | `validation_gate:scale_unknown` |
| NIC | document-family policy gap | `validation_gate:scale_unknown` |
| DXC | selected-table scale plus label guard | `validation_gate:metric_label_mismatch:ebit:net_operating_income` |
| HUB | period-source fail-closed control | `validation_gate:announcement_date_period_end` |
| LBL | selected-table scale risk plus period fail-closed | `validation_gate:announcement_date_period_end` |
| CTN | period-source mismatch control | `validation_gate:period_source_mismatch` |
| CXO | clean scale-known control | `ok` |
| EQR | clean noncandidate control | `validation_gate:source_noncandidate:meeting_or_proxy_notice` |

## Audit Answers

Selected-table scale binding is required for DXC/LBL-class cases, but only when
explicit table-local evidence exists and all other truth gates pass. LBL remains
blocked by period evidence before scale repair can matter.

Same-page scale propagation is a candidate path for AZJ only. EDU is explicitly
excluded from same-page propagation because selected surfaces are mixed and
unclean. A production same-page propagation repair is not justified until a
second clean same-page case proves the same metric-local source-bound root
cause.

Mixed or unclean cases that must fail closed: EDU, HUB, LBL, and CTN.

Parser/table coverage gaps: WHC, AZJ, EDU, and DXC.

Policy gaps: NIC webcast-details document-family policy and AZJ nearest-$100k
rounding policy.

Future sample artifacts must capture document identity, selected table/page,
table headers, table-local scale, same-page scale, document-level scale, metric
row/cell text, raw and normalized values, row refs, `metric_source_scales`,
`metric_scale_sources`, and `_common_metric_source_scale` input/output.

## Fix Made

No production extraction repair was made.

Safe extension made: harness-only evaluation/reporting change in
`financial-engine_v2/scripts/broad_extraction_test.py`, focused tests, and
contract documentation for the provenance artifact floor.

## Count-24 / Count-32 Decision

Count-24 rerun is not justified. The harness does not prove one repeated
production repair root cause across at least two clean cases.

Count-32 remains blocked and still requires a separate approval path after a
source-bound repair and count-24 approval packet.

## DATA_MISSING

- Runtime row refs for count-24 accepted and failed rows are not consistently
  present.
- Exact selected table/page provenance for NIC, DXC, HUB, LBL, CTN, and CXO is
  not present in current artifacts.
- Metric-local same-page scale binding is captured for AZJ/EDU only and remains
  incomplete for a repeated repair.
- Source-bound nearest-$100k policy for AZJ remains unresolved.

## Files Touched

- `docs/agent_tasks/extraction_scale_table_provenance_harness_v1_20260607.md`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/README.md`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/status.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/harness_manifest.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/evidence_table.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/root_cause_grouping.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/repair_decision.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/validation.json`
- `reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/diff-check.json`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `docs/extraction/metric_extraction_contract.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- Source PDFs
- DB, Qdrant, Redis, news stores, memory, prompts, gold labels, runtime config,
  model config, GPU config, schema, and production data

## Validation Status

See `validation.json`.

Summary:

- Task card validate: pass.
- Registry `list-active --read-only`: pass, no active jobs.
- JSON validation: pass.
- Focused pytest: pass, `6 passed`.
- `py_compile`: pass.
- `ruff`: pass.
- `git diff --check`: pass.
- Task-card `check-diff`: pass.
- Source-PDF audit: no PDF paths reported.

Report artifacts live under ignored `reports/`; the task-card `check-diff`
sees the visible code/docs/task-card changes and writes `diff-check.json`.

## Unsafe Actions Avoided

- No count-24 rerun.
- No count-32.
- No random sample.
- No broad extraction/backfill.
- No full ticker-universe extraction.
- No DB/Qdrant/Redis/news/memory mutation.
- No source PDF edits.
- No prompt/gold-label/runtime/schema changes.
- No broad scale inference.
- No truth gate loosening.
- No dirty parent-batch merge.

## Next Recommended Prompt

```text
/goal Build a no-write metric-local same-page scale provenance capture for AZJ plus one additional clean same-page scale candidate from the fixed scale-table harness. Use reports/agent_jobs/extraction_scale_table_provenance_harness_v1_20260607/harness_manifest.json as the case contract. Do not run count-24, count-32, random samples, broad extraction, or backfill. Keep EDU mixed selected surfaces fail-closed. Implement one narrow same-page scale propagation repair only if at least two clean cases prove the same source-bound row/page root cause with row_refs, metric_source_scales, metric_scale_sources, selected table/page, and common-scale trace.
```
