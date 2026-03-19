#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python}"
PYTEST_BIN="${PYTEST_BIN:-${ROOT_DIR}/financial-engine_v2/.venv/bin/pytest}"

if [[ "${PYTHON_BIN}" == "python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/financial-engine_v2/.venv/bin/python"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "[FAIL] python runtime not found or not executable: ${PYTHON_BIN}" >&2
  exit 2
fi

if [[ ! -x "${PYTEST_BIN}" ]]; then
  echo "[FAIL] pytest runtime not found or not executable: ${PYTEST_BIN}" >&2
  exit 2
fi

run_step() {
  local name="$1"
  shift

  echo "[RUN] ${name}"
  if "$@"; then
    echo "[PASS] ${name}"
    return 0
  fi

  local rc=$?
  echo "[FAIL] ${name} (rc=${rc})" >&2
  exit "${rc}"
}

run_step "ruff" \
  "${PYTHON_BIN}" -m ruff check autodev financial-engine_v2/backend scripts

run_step "backend-tests" \
  "${PYTEST_BIN}" -c pytest.ini financial-engine_v2/backend/tests -q

run_step "autodev-tests" \
  "${PYTEST_BIN}" -c pytest.ini autodev/tests -q

run_step "scripts-tests" \
  "${PYTEST_BIN}" -c pytest.ini scripts -q

run_step "canonical-dataset-checks" \
  bash scripts/run_canonical_dataset_checks.sh

run_step "canonical-regression" \
  "${PYTHON_BIN}" scripts/check_canonical_regression.py \
    --baseline reports/baselines/canonical_eval_baseline_latest.json \
    --news-report reports/news_eval_report.json \
    --company-report reports/company_eval_report_v2.json \
    --reference-report reports/eval_queries_report.json

run_step "financial-metrics-gates" \
  "${PYTHON_BIN}" scripts/validate_financial_metrics_gates.py \
    reports/financial_metrics.json \
    --out-json reports/financial_metrics.gates.json

run_step "financial-coverage-gates" \
  "${PYTHON_BIN}" scripts/validate_financial_coverage_gates.py \
    reports/financial_metrics.json \
    --out-json reports/financial_metrics.coverage_gates.json

echo "[PASS] stable-baseline"
