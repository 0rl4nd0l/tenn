# Post-PR299 Broad Accuracy Push

Generated: 2026-06-06T04:00:19.053806+00:00

State: DONE_WITH_RISK.

Final decision: `NEEDS_ACCEPTED_OUTPUT_AUDIT`.

## Objective

Push Tenn extraction closer to broad accuracy after PR #299 by completing the
next safe sequence: candidate-exclusion taxonomy repair, one bounded count-16
validation sample, and at most one narrow follow-up repair if evidence supports
it.

## Phases Completed

- Phase 1 candidate-exclusion taxonomy: completed and committed in `9c9107bb`.
- Phase 2 bounded count-16 validation: completed exactly once and committed in
  `12e60429`.
- Phase 3 failure taxonomy plus one narrow repair: completed and committed in
  `e9703b3c`.
- Phase 4 stop decision: `NEEDS_ACCEPTED_OUTPUT_AUDIT`.

## Commits Created

- `85b05a92` - create parent task card/report.
- `9c9107bb` - add post-PR299 source exclusion taxonomy.
- `12e60429` - run post-PR299 count-16 validation.
- `e9703b3c` - classify count-16 failures and bind table scale.

## Count-16 Result

- total: 16
- ok: 9
- ok_low_confidence: 0
- failed: 7
- exceptions: 0
- failure taxonomy: `{"source_noncandidate:board_change_notice": 1, "source_noncandidate:meeting_or_proxy_notice": 1, "source_noncandidate:operational_project_update": 1, "source_noncandidate:pre_results_segment_re_presentation": 1, "source_noncandidate:share_sale_or_gross_proceeds_announcement": 1, "validation_gate:period_source_mismatch": 1, "validation_gate:scale_unknown": 1}`
- low-confidence taxonomy: `{}`
- unsafe row check: `{"negative_revenue": [], "nonpositive_shares": []}`

The sample was comparable to the post-PR297 count-16 sample by seed and candidate
pool hashes. No count-24/count-32 was run.

## Failure And Risk Taxonomy

- true noncandidate: EQR, MAH, FCL, HRZ, and MPL. Phase 1 exclusions behaved as
  intended.
- parser/table coverage gap plus missing scale evidence: WHC 2022 annual report,
  `validation_gate:scale_unknown`.
- period/source mismatch: CTN Appendix 5B quarterly report, where source-period
  evidence missed singular quarterly activity / Appendix 5B wording and was
  distracted by a historical annual-report phrase.
- accepted-output risk: DXC confirmed selected-table scale-binding error; LBL
  suspicious presentation/chart scale acceptance; AZJ nearest-$100,000 rounding
  policy not yet represented.

## Narrow Repair Implemented

Implemented selected-table scale propagation in
`financial-engine_v2/backend/app/services/multipass_extraction.py`: a selected
local table scale marker such as `$'000` now overrides an earlier document-level
scale during metric extraction, and a common metric source scale can flow into
the reconciled payload/source-bound scale. Focused tests were added in
`financial-engine_v2/backend/tests/test_multipass_extraction.py`.

The repair is source-bound and directly targets the DXC evidence. It does not
claim to solve WHC parser/table coverage, CTN period evidence, AZJ rounding
policy, or LBL chart/table ambiguity.

## Side-Effect Audit

- DB changed: None
- Qdrant changed: None
- Queues clean after: None
- News route used: None
- Memory mutated: None
- Source PDFs changed: None

## Validation Results

- Phase 1: focused pytest, py_compile, ruff, JSON validation, git diff checks,
  task-card check-diff, no source PDFs staged: passed.
- Phase 2: one count-16 run, JSON validation, runner py_compile, git diff
  checks, task-card check-diff, no source PDFs staged: passed.
- Phase 3: focused pytest and full touched backend test file, py_compile, ruff,
  JSON validation, git diff checks, task-card check-diff, no source PDFs staged:
  passed.
- Parent Phase 4 validation: task-card validate, JSON validation, git diff
  checks, task-card check-diff, no source PDFs staged, and registry/list-active
  evidence passed with the read_only=false registry caveat.

## DATA_MISSING

- Post-repair runtime outcome for DXC/LBL/AZJ/WHC/CTN was not measured; Phase 3
  did not run another sample.
- Reliable GPU memory telemetry remains unavailable from Phase 2 preflight.
- Safe read-only registry proof remains unavailable because the local
  `list-active` command reports `read_only=false`.
- Docling-native behavior for the selected-table scale repair was not proven by
  rerunning DXC/LBL; deterministic unit coverage passed.

## Files Touched

- Parent and child task cards under `docs/agent_tasks/`.
- Parent and child report artifacts under `reports/agent_jobs/`.
- `financial-engine_v2/backend/app/services/multipass_extraction.py`.
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`.
- `financial-engine_v2/scripts/broad_extraction_test.py` and
  `financial-engine_v2/scripts/test_broad_extraction_test.py` from Phase 1
  taxonomy-scorecard alignment.
- `docs/extraction/metric_extraction_contract.md` and
  `docs/architecture/12_evaluation_and_drift_monitoring.md` from Phase 1 docs.

## Files Intentionally Not Touched

No source PDFs, DB/Qdrant/news/memory stores, prompts, gold labels, schemas,
runtime/model/GPU configuration, production services, broad backfill paths, or
full ticker-universe extraction paths were changed.

## Unsafe Actions Avoided

No broad extraction, no backfill, no full ticker-universe extraction, no
count-24/count-32, no direct SQL mutation, no Qdrant/news/memory mutation, no
source PDF edits, no prompt/gold-label/runtime/schema changes, no service
restart beyond bounded validation needs, no unrelated cleanup, and no dirty
NVMe parent-batch merge.

## GitHub Update

Issue #96 comment posted: https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4637305661. No close, relabel, assignment, or milestone mutation was performed.

## Exact Next Recommended Task

Create a bounded accepted-output audit task for DXC/LBL/AZJ presentation/table
scale and rounding-policy risks before any count-24 approval packet. Do not run
count-24/count-32 until that audit resolves unsafe accepted-output risk.
