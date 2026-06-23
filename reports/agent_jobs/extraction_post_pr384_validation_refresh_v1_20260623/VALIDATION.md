# Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Task card validate | PASS | `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr384_validation_refresh_v1_20260623.md` |
| Initial diff scope | PASS | `python3 scripts/agent_job_contract.py check-diff ... --no-write-report` |
| Pytest fallback self-test | PASS | `pytest_fallback_selftest.json`, mode `ephemeral_overlay`, `8 passed` |
| Focused JAY pytest target | PASS | `pytest_market_update.json`, mode `ephemeral_overlay`, `3 passed, 204 deselected` |
| JAY canonical replay | PASS | `jay_canonical_replay/validation.json`, side effects clean |
| Compatible guard replay | PASS | `guard_replay/validation.json`, side effects clean |
| WHC/EDU mixed-unit replay | PASS | `whc_edu_replay/validation.json`, side effects clean |
| Pytest overlay cleanup | PASS | no `/tmp/tenn-pytest-overlay-*` directories remained |

## Runtime Functionality Proof

- Intended output: report-local validation artifacts under `reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623`.
- Live output location: the report directory in this worktree.
- Pre-run max timestamp or count: no files existed in this report directory before the task card was created.
- Post-run max timestamp or count: replay artifacts, pytest reports, matrix, and board files exist under the report directory.
- Rows/files inserted or updated after run start: report-local files only.
- Readiness/gate status: validation refresh ready; no product fix approved from this run.
- Exact command/query used: see the command table above and replay artifact `input_manifest.json` files.
- Result: `WORKING`
- Remaining blocker: DXC/WHC row fixes require exact source-row proof before implementation.

## Replay Commands

```bash
python3 scripts/run_pytest_with_fallback.py --base-python "$(command -v python3)" --report-json reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/pytest_fallback_selftest.json -- scripts/test_run_pytest_with_fallback.py -q
python3 scripts/run_pytest_with_fallback.py --base-python /home/l4nd0/tenn-extraction-no-write-replay-harness-v1-20260618/financial-engine_v2/.venv/bin/python --report-json reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/pytest_market_update.json -- financial-engine_v2/backend/tests/test_multipass_extraction.py -k market_update_net_revenue_candidate -q
financial-engine_v2/.venv/bin/python scripts/extraction_no_write_replay.py --profile docling-no-write --venv-python financial-engine_v2/.venv/bin/python --case-manifest financial-engine_v2/data/extraction_no_write_cases/jay_market_update_cases_v1.json --case all --report-dir reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/jay_canonical_replay --llm-base-url http://127.0.0.1:8001 --case-timeout-seconds 900
financial-engine_v2/.venv/bin/python scripts/extraction_no_write_replay.py --profile docling-no-write --venv-python financial-engine_v2/.venv/bin/python --case-manifest financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json --case CTN --case HUB --case LBL --case AZJ --case NSR --report-dir reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/guard_replay --llm-base-url http://127.0.0.1:8001 --case-timeout-seconds 900
financial-engine_v2/.venv/bin/python scripts/extraction_no_write_replay.py --profile docling-no-write --venv-python financial-engine_v2/.venv/bin/python --case-manifest financial-engine_v2/data/extraction_no_write_cases/whc_edu_mixed_unit_cases_v1.json --case all --report-dir reports/agent_jobs/extraction_post_pr384_validation_refresh_v1_20260623/whc_edu_replay --llm-base-url http://127.0.0.1:8001 --case-timeout-seconds 900
```
