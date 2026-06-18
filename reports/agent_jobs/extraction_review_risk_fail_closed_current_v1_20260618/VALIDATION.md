# Validation

Validation completed.

Commands:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md --write-report`
  - Result: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md --repo-root .`
  - Result: passed; no active overlap.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md --repo-root .`
  - Result: passed.
- `python3 -m py_compile financial-engine_v2/scripts/broad_extraction_test.py financial-engine_v2/scripts/test_broad_extraction_test.py reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/saved_artifact_replay.py`
  - Result: passed.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q`
  - Result: passed, 13 tests.
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python reports/agent_jobs/extraction_review_risk_fail_closed_current_v1_20260618/saved_artifact_replay.py`
  - Result: passed; `ok: true`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md --repo-root .`
  - Result: passed; no disallowed visible files.
- `git diff --check`
  - Result: passed.
- Report JSON syntax check for all report JSON files
  - Result: passed.
- `python3 scripts/agent_job_registry.py release extraction_review_risk_fail_closed_current_v1_20260618 --repo-root .`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_review_risk_fail_closed_current_v1_20260618.md --repo-root .`
  - Result: passed.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Result: passed; `active_jobs: []`.
- Original checkout status recheck
  - Result: pre-existing unrelated dirt unchanged.

Saved-artifact replay checks:

- `whc_edu_reclassified`: true.
- `nsr_cae_remain_accepted_info`: true.
- `risk_flags_preserved`: true.
- `no_pdf_extraction_invoked`: true.

Projected summary:

- Status distribution: 14 `failed`, 9 `ok`, 1 `ok_low_confidence`.
- New grouped error: `validation_gate:accepted_output_scale_magnitude_risk` = 2.

Not run:

- No count-24 rerun.
- No count-32, random sample, broad extraction, backfill, full-universe
  extraction, production repair, runtime service start, or data-store mutation.
