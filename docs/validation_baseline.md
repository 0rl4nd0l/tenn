# Validation Baseline (2026-03-19)

This runbook captures the validated command sequence for the current stable baseline.

## Command Sequence

```bash
bash scripts/start_system.sh
bash scripts/validate_system.sh
python -m ruff check autodev financial-engine_v2/backend scripts
pytest autodev/tests
pytest financial-engine_v2/backend/tests
pytest scripts
bash scripts/run_canonical_dataset_checks.sh
python scripts/check_canonical_regression.py --baseline reports/baselines/canonical_eval_baseline_latest.json --news-report reports/news_eval_report.json --company-report reports/company_eval_report_v2.json --reference-report reports/eval_queries_report.json
python scripts/validate_financial_metrics_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.gates.json
python scripts/validate_financial_coverage_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.coverage_gates.json
```

## Passing Gate Set
- Ruff check on `autodev`, `financial-engine_v2/backend`, and `scripts`
- Pytest on `autodev/tests`, `financial-engine_v2/backend/tests`, and `scripts`
- Canonical dataset eval + canonical regression baseline check
- Financial metrics gates
- Financial coverage gates

## Environment Notes
- In restricted socket environments, health/smoke checks may print `SKIP due restricted environment`. This is expected and non-fatal.
- Canonical dataset checks support CPU fallback by default (`REQUIRE_CUDA=0`).
- Set `REQUIRE_CUDA=1` only when CUDA must be enforced.

## Canonical Regression Fixtures
- `reports/baselines/canonical_eval_baseline_latest.json`
- `reports/news_eval_queries.json`
- `reports/company_eval_queries.json`
- `reports/eval_queries.json`

## Tool Pin Notes
- `ruff` is pinned in `financial-engine_v2/backend/requirements.txt` and inherited by the root `requirements.txt` include chain.
