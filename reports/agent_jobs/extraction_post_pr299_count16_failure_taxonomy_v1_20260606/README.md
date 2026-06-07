# Post-PR299 Count-16 Failure Taxonomy

Generated: 2026-06-06T03:55:47.144273+00:00

State: DONE_WITH_RISK. Phase 3 audited the one post-PR299 count-16 sample and
implemented one narrow source-bound repair.

## Input Sample

- Phase 2 report: `reports/agent_jobs/extraction_post_pr299_count16_validation_v1_20260606`
- ok: 9
- ok_low_confidence: 0
- failed: 7
- exceptions: 0
- low-confidence taxonomy: `{}`

## Failure Taxonomy

- true noncandidate: 5 (EQR, MAH, FCL, HRZ, MPL). These are expected exclusions
  from Phase 1 and do not need another taxonomy repair.
- parser/table coverage gap plus eligible doc missing scale evidence: 1 (WHC
  2022 annual report, `validation_gate:scale_unknown`).
- period/source mismatch: 1 (CTN Appendix 5B quarterly report, source-period
  evidence currently distracted by a historical annual-report phrase).
- accepted-output risk: 3 audited accepted rows (DXC confirmed selected-table
  scale-binding error; LBL suspicious chart/table scale; AZJ rounding policy).

## Repair Implemented

Implemented source-bound selected-table scale propagation in
`financial-engine_v2/backend/app/services/multipass_extraction.py` with focused
unit coverage in `financial-engine_v2/backend/tests/test_multipass_extraction.py`.
The direct evidence is DXC: a selected `Consolidated profit & loss statement`
table marked `$'000` was accepted as `millions` in Phase 2.

## Not Repaired In This Phase

- WHC 2022 parser/table coverage gap.
- CTN Appendix 5B / singular quarterly activity period-evidence gap.
- AZJ nearest-$100,000 rounding policy.
- LBL suspicious presentation/chart scale acceptance.

## Validation

- Phase 3 task-card validate: passed.
- Focused pytest for selected-table scale repair: passed, 3 selected tests.
- Full touched backend test file: passed, 177 tests, 1 warning.
- py_compile: passed.
- ruff: passed.
- JSON validation: passed.
- git diff --check: passed.
- task-card check-diff: passed, disallowed_files empty.
- no source PDFs staged: passed.
- registry/list-active: active_jobs empty, with read_only=false caveat.

## Unsafe Actions Avoided

No broad extraction, no backfill, no full ticker-universe extraction, no
count-24/count-32, no direct SQL mutation, no Qdrant/news/memory mutation, no
source PDF edits, and no prompt/gold-label/runtime/schema changes.

## DATA_MISSING

- Post-repair runtime outcome for DXC/LBL/AZJ/WHC/CTN was not measured; no
  additional sample was run in Phase 3.
- Reliable GPU memory telemetry remains unavailable from Phase 2 preflight.
- Safe read-only registry proof remains unavailable because the available
  registry command reports `read_only=false`.

## Recommended Phase 4 Decision

`NEEDS_ACCEPTED_OUTPUT_AUDIT`.
