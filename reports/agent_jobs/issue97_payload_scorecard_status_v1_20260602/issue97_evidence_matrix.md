# Issue #97 Evidence Matrix

| Evidence | Current path or link | Finding | #97 impact |
| --- | --- | --- | --- |
| GitHub issue | https://github.com/0rl4nd0l/tenn/issues/97 | Issue is open with `state:data-missing` and `state:needs-review`. | Keep open. |
| Initial #97 issue comment | GitHub issue comment, 2026-05-26 | Confirmed metric coverage has 15 fixtures, 146 expectations, and 73 scored-ready expectations, but actual payload maps were missing. | Original blocker confirmed. |
| Scorecard builder | `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py` | `build_confirmed_metric_payload_scorecard()` and `PayloadScoreStatus` exist on current branch. | Plumbing exists. |
| Builder report | `reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/README.md` | Report-local synthetic sample proved schema and classifications, not live broad accuracy. | Partial implementation only. |
| CLI gate | `reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/README.md` | CLI profile `confirmed_metric_payload` requires `--actuals-json` and can emit pre-persistence gate. | Reproducibility improved. |
| Actuals coverage gate | `reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/README.md` | Gate reports matched/unmatched actual payload ids and fails on unmatched documents. | Prevents false pass. |
| Canary actual exporter | `reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/README.md` | Seven accepted canary actual payloads exported from SQLite read-only, but were unmatched by confirmed metric fixture scope. | Useful evidence, not #97 completion. |
| Source-review bridge | `reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/README.md` | Seven canary actuals matched source-reviewed fixtures; first pass found AAU/AQX/ATM blockers. | Shows gate catches real blockers. |
| Post-ATM rerun | `reports/agent_jobs/extraction_post_atm_scale_fix_canary_rerun_v1_20260601/README.md` | Seven bounded source-reviewed canaries passed after ATM scale fix. | Strong bounded canary proof, not full confirmed profile proof. |
| #98 parity guard | `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/README.md` and PR #206 | Metric contract parity guard exists and #98 is closed; #97 still needs actual payload evidence. | Removes one dependency, not all. |
| PR search | `gh pr list --search "#97 OR confirmed_metric_extracted_payload_scorecard OR confirmed_metric_payload OR payload scorecard"` | Found related PRs #131 and #206; no exact #97 closeout PR. | No duplicate closeout. |
