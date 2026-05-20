# DATA_MISSING - Gold Metric Coverage Audit v1

- Current generated real-gold run artifacts were not found under `reports/extraction_real_eval_results*` in this worktree.
- Current generated confirmed coverage artifacts were not found under `reports/extraction_eval/confirmed_metric_coverage_review_*` in this worktree.
- `financial-engine_v2/backend/tests/eval_results/` has no current live extraction result artifact in this worktree.
- The current branch does not contain `scripts/run_extraction_evaluation_gates.py`, `scripts/run_appendix5b_no_regression_gate.py`, `scripts/test_extraction_evaluation_gates.py`, or `scripts/test_appendix5b_no_regression_gate.py`.
- Appendix 5B evidence found in `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/` is approval-packet evidence only here; the packet says the PRM metric was not added to a gate.
- `source_url` is `DATA_MISSING` for all current `financial-engine_v2/data/extraction_gold_real/*.json` fixtures.
- Several docs/specs conflict with current code or fixtures: `docs/architecture/12_evaluation_and_drift_monitoring.md` says 13 eval fixtures while current `backend/tests/eval_fixtures` has 15; `financial-engine_v2/backend/tests/eval_config.json` refers to a 6-fixture regression gate; `docs/extraction/supplemental_metric_normalization_registry.yaml` records an older 10-doc/22-datapoint canonical lane while the current profile code expects 10 docs/24 checks.
- Broad production coverage acceptance criteria for Tier 2/Tier 3 metrics are not fully defined. In particular, EBITDA, EPS, free cash flow, margins, ratios, segment metrics, and derived net debt need source definitions and schema support before hard scoring.
- No current extracted payloads were supplied to `confirmed_metric_coverage` during this audit, so confirmed coverage is an inventory/readiness profile, not a fresh extraction accuracy score.
