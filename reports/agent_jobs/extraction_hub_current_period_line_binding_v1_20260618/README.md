# HUB Current-Period Line Binding

State: `DONE_WITH_RISK`
Decision: `DRAFT_PR_OPENED`
Generated: `2026-06-18`

Draft PR:
https://github.com/0rl4nd0l/tenn/pull/376

## Objective

Implement the narrow HUB period/source ambiguity fix proven by the prior
read-only evidence packet.

## Result

Implemented one deterministic source-bound fix in
`financial-engine_v2/backend/app/services/multipass_extraction.py`.

The detector now recognizes exact source-text `Current period: <start> to
<end>` half-year ranges and uses that current-period evidence to resolve
otherwise ambiguous same-document period-end hits only when the other conflicting
hits are comparative/prior context. True conflicts still return `ambiguous`.

## Files Changed

- `docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- Report artifacts under:
  `reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/`

## Validation

- RED evidence captured by implementation worker.
- Focused keyword suite: `10 passed, 19 deselected`.
- Full pre-canary truth-gate file: `29 passed`.
- `py_compile`: passed.
- `git diff --check`: passed.
- `check-diff --no-write-report`: passed.

No extraction, count rerun, DB/Qdrant/Redis/news/memory/source-PDF/gold-label/
prompt/runtime/model/GPU/service mutation was performed. GitHub mutation is now
limited to pushing this branch and opening/updating draft PR #376.
