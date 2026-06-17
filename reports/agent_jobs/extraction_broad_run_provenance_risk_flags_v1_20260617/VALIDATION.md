# Validation

## RED

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q -p no:cacheprovider financial-engine_v2/scripts/test_broad_extraction_test.py -k "broad_run"
```

Result: exit `1`

Expected failures:

- missing `_build_metric_provenance_audit`
- missing `_build_scale_magnitude_risk`
- missing `provenance_coverage` summary rollup

## GREEN And Checks

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q -p no:cacheprovider financial-engine_v2/scripts/test_broad_extraction_test.py -k "broad_run"
```

Result: exit `0`, `3 passed, 6 deselected`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q -p no:cacheprovider financial-engine_v2/scripts/test_broad_extraction_test.py
```

Result: exit `0`, `9 passed`.

```bash
PYTHONPYCACHEPREFIX=/tmp/tenn-broad-run-provenance-risk-flags-pycache /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/scripts/broad_extraction_test.py
```

Result: exit `0`.

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/scripts/broad_extraction_test.py financial-engine_v2/scripts/test_broad_extraction_test.py
```

Result: exit `0`, `All checks passed!`.

```bash
git diff --check
```

Result: exit `0`.

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md --write-report
```

Result: exit `0`, `ok: true`; wrote `validation.json`.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`, `disallowed_files: []`; wrote `diff-check.json`.

## Not Run

- No count-24, count-32, broad extraction, broad backfill, full ticker-universe extraction, runtime service start, DB write, Qdrant write, Redis write, news write, memory write, source PDF edit, prompt edit, gold-label edit, schema change, or GitHub mutation.
